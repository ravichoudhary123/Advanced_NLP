import Foundation

@MainActor
final class ImportViewModel: ObservableObject {
    @Published var pastedText: String = ""
    @Published var title: String = "Pasted Book"
    @Published var lastImportError: String?

    private let importService: ImportService
    private let repository: AudiobookRepository

    init(importService: ImportService, repository: AudiobookRepository) {
        self.importService = importService
        self.repository = repository
    }

    func importPastedText() {
        do {
            let book = try importService.importText(pastedText, suggestedTitle: title)
            try repository.saveBook(book)
            pastedText = ""
        } catch {
            lastImportError = error.localizedDescription
        }
    }

    func importFile(url: URL) {
        do {
            let book = try importService.importFile(at: url)
            try repository.saveBook(book)
        } catch {
            lastImportError = error.localizedDescription
        }
    }
}
