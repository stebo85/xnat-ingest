# Native DICOM classification for AIS edge

`get_xnat_resource` selects the XNAT scan datatype separately from the resource
directory. Raw Data Storage, MR Spectroscopy, Presentation State, and Multi-frame
Grayscale Word Secondary Capture use `OtherDicomScanData` and `secondary`.
Enhanced MR Color Image Storage uses `MrScanData` and `secondary`. Ordinary MR
and monochrome Enhanced MR retain their usual `DICOM` resources. Resource names
are normalized on repeat imports as well as when creating a scan.

`Dockerfile.ais-edge` preserves the production v5 dependency image by digest and
copies this branch's native upload module into it. The ordinary `Dockerfile`
also installs the fix when building the complete package from source. The
compatibility build intentionally keeps the other AIS edge fixes in their
existing deployment wrapper; it does not replace the whole dependency stack.

Build and test the compatibility image:

```sh
docker build -f Dockerfile.ais-edge --build-arg SOURCE_REVISION="$(git rev-parse HEAD)" -t xnat-ingest-native .
docker run --rm --network none --entrypoint python3 -v "$PWD/tests:/tests:ro" \
  xnat-ingest-native -m unittest discover -s /tests -p test_dicom_scan_classification.py -v
```

After publication, select the image by digest in AIS edge's management config
and upload Deployment. Remove the guarded classification source-rewriting block
from `manifests/01-management/xnat-upload.yaml.tpl`, retaining the other patches.
The wrapper can require `NATIVE_DICOM_CLASSIFICATION_VERSION == 1` to fail clearly
if someone selects an older image. Keep the edge sorter on its existing image;
this release changes the management uploader only.
