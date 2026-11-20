import SwiftUI
import VisionKit

/// The system document camera (edge detection, perspective fix). Pages come back as images and are read with OCR.
struct DocumentScanner: UIViewControllerRepresentable {
    var onDone: ([CGImage]) -> Void
    var onCancel: () -> Void

    static var isAvailable: Bool { VNDocumentCameraViewController.isSupported }

    func makeUIViewController(context: Context) -> VNDocumentCameraViewController {
        let vc = VNDocumentCameraViewController()
        vc.delegate = context.coordinator
        return vc
    }

    func updateUIViewController(_ vc: VNDocumentCameraViewController, context: Context) {}
    func makeCoordinator() -> Coordinator { Coordinator(self) }

    final class Coordinator: NSObject, VNDocumentCameraViewControllerDelegate {
        let parent: DocumentScanner
        init(_ p: DocumentScanner) { parent = p }

        func documentCameraViewController(_ c: VNDocumentCameraViewController, didFinishWith scan: VNDocumentCameraScan) {
            parent.onDone((0 ..< scan.pageCount).compactMap { scan.imageOfPage(at: $0).cgImage })
        }
        func documentCameraViewControllerDidCancel(_ c: VNDocumentCameraViewController) { parent.onCancel() }
        func documentCameraViewController(_ c: VNDocumentCameraViewController, didFailWithError error: Error) { parent.onCancel() }
    }
}
