"""Exercise the upload factory without an XNAT server or test data download."""

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from xnat_ingest.helpers.remotes import get_xnat_resource


class MrSession:
    pass


class PetSession:
    pass


class DicomClassificationTest(unittest.TestCase):
    def factory(self, metadata, name="DICOM"):
        created = []
        session = MrSession()
        session.scans = {}
        session.id = "TEST_E1"
        session.label = "test-session"

        def constructor(kind):
            def create(**kwargs):
                created.append(kind)
                scan = SimpleNamespace(resources={}, files=["test.dcm"], **kwargs)
                scan.create_resource = lambda label: SimpleNamespace(label=label)
                session.scans[kwargs["id"]] = scan
                return scan
            return create

        session.xnat_session = SimpleNamespace(classes=SimpleNamespace(
            MrSessionData=MrSession, PetSessionData=PetSession,
            OtherDicomScanData=constructor("other"), MrScanData=constructor("mr"),
            ScScanData=constructor("sc"), PetScanData=constructor("pet"),
            CtScanData=constructor("ct"),
        ))
        scan = SimpleNamespace(id="1", type="test-series", path="1.test-series",
                               session=SimpleNamespace(path="test-session"))
        resource = SimpleNamespace(name=name, metadata=metadata, scan=scan,
                                   checksums={"test.dcm": "checksum"})
        return session, resource, created

    def test_datatype_and_resource_are_independent(self):
        cases = [
            ("1.2.840.10008.5.1.4.1.1.11.3", "PR", "other", "secondary"),
            ("1.2.840.10008.5.1.4.1.1.4.2", "MR", "other", "secondary"),
            ("1.2.840.10008.5.1.4.1.1.7.3", "MR", "other", "secondary"),
            ("1.2.840.10008.5.1.4.1.1.66", "MR", "other", "secondary"),
            ("1.2.840.10008.5.1.4.1.1.4.3", "MR", "mr", "secondary"),
            ("1.2.840.10008.5.1.4.1.1.4", "MR", "mr", "DICOM"),
            ("1.2.840.10008.5.1.4.1.1.4.1", "MR", "mr", "DICOM"),
        ]
        for sop, modality, datatype, label in cases:
            with self.subTest(sop=sop):
                session, resource, created = self.factory(
                    {"SOPClassUID": sop, "Modality": modality})
                result = get_xnat_resource(resource, session)
                self.assertEqual(created, [datatype])
                self.assertEqual(result.label, label)

    def test_sop_mapping_precedes_derived_secondary_heuristic(self):
        for sop, datatype in [("1.2.840.10008.5.1.4.1.1.66", "other"),
                              ("1.2.840.10008.5.1.4.1.1.4.3", "mr")]:
            with self.subTest(sop=sop):
                session, resource, created = self.factory({
                    "SOPClassUID": sop, "Modality": "MR",
                    "ImageType": ["DERIVED", "SECONDARY"],
                })
                self.assertEqual(get_xnat_resource(resource, session).label, "secondary")
                self.assertEqual(created, [datatype])

    def test_repeated_import_reuses_secondary_resource(self):
        for sop in ["1.2.840.10008.5.1.4.1.1.66", "1.2.840.10008.5.1.4.1.1.4.3"]:
            with self.subTest(sop=sop):
                session, resource, created = self.factory({"SOPClassUID": sop, "Modality": "MR"})
                existing = get_xnat_resource(resource, session)
                session.scans["1"].resources["secondary"] = existing
                with patch("xnat_ingest.helpers.remotes.get_xnat_checksums",
                           return_value=resource.checksums) as checksums:
                    self.assertIsNone(get_xnat_resource(resource, session))
                    checksums.assert_called_once_with(existing)
                self.assertEqual(len(created), 1)
                self.assertEqual(list(session.scans["1"].resources), ["secondary"])

    def test_non_dicom_resource_keeps_its_name_and_modality(self):
        session, resource, created = self.factory(
            {"SOPClassUID": "1.2.840.10008.5.1.4.1.1.66", "Modality": "MR"}, name="NIFTI")
        self.assertEqual(get_xnat_resource(resource, session).label, "NIFTI")
        self.assertEqual(created, ["mr"])

    def test_missing_metadata_preserves_session_default(self):
        session, resource, created = self.factory(None)
        self.assertEqual(get_xnat_resource(resource, session).label, "DICOM")
        self.assertEqual(created, ["mr"])


if __name__ == "__main__":
    unittest.main()
