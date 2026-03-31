import Foundation

struct PlaceholderEPUBImportService: EPUBImportService {
    func importEPUB(at url: URL) throws -> Audiobook {
        throw NSError(domain: "EPUB", code: 100, userInfo: [NSLocalizedDescriptionKey: "EPUB import is scaffolded. Integrate EPUBKit/ZIP parser in this adapter."])
    }
}
