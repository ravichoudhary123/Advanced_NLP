import Foundation
import PDFKit

struct DefaultImportService: ImportService {
    let parser: DefaultTextParser

    func importText(_ text: String, suggestedTitle: String) throws -> Audiobook {
        let chapters = parser.parseChapters(from: text)
        return buildBook(title: suggestedTitle, sourceType: .pasted, chapters: chapters)
    }

    func importFile(at url: URL) throws -> Audiobook {
        switch url.pathExtension.lowercased() {
        case "txt":
            let text = try String(contentsOf: url)
            let parsed = parser.parseChapters(from: text)
            return buildBook(title: url.deletingPathExtension().lastPathComponent, sourceType: .txt, sourceFileName: url.lastPathComponent, chapters: parsed)
        case "pdf":
            let text = try extractPDFText(from: url)
            let parsed = parser.parseChapters(from: text)
            return buildBook(title: url.deletingPathExtension().lastPathComponent, sourceType: .pdf, sourceFileName: url.lastPathComponent, chapters: parsed)
        case "epub":
            throw NSError(domain: "Import", code: 2, userInfo: [NSLocalizedDescriptionKey: "EPUB parser scaffolded; implement EPUBImportService adapter."])
        default:
            throw NSError(domain: "Import", code: 1, userInfo: [NSLocalizedDescriptionKey: "Unsupported format"])
        }
    }

    private func extractPDFText(from url: URL) throws -> String {
        guard let pdf = PDFDocument(url: url) else {
            throw NSError(domain: "Import", code: 3, userInfo: [NSLocalizedDescriptionKey: "Failed to open PDF"])
        }

        var text = ""
        for index in 0..<pdf.pageCount {
            text += pdf.page(at: index)?.string ?? ""
            text += "\n"
        }
        return text
    }

    private func buildBook(title: String, sourceType: AudiobookSourceType, sourceFileName: String? = nil, chapters: [ParsedChapter]) -> Audiobook {
        let chapterModels = chapters.enumerated().map { offset, chapter in
            Chapter(index: offset, title: chapter.title, rawText: chapter.text)
        }

        let book = Audiobook(title: title, sourceType: sourceType, sourceFileName: sourceFileName, chapters: chapterModels)
        chapterModels.forEach { $0.book = book }
        return book
    }
}
