import Foundation

enum SampleDataSeeder {
    @MainActor
    static func seedIfNeeded(repository: AudiobookRepository) async {
        let existing = try? repository.fetchBooks(search: nil)
        guard existing?.isEmpty ?? true else { return }

        let text = """
        Chapter 1

        OpenAudioBooksIPad is an iPad-first audiobook builder.

        Chapter 2

        This sample demonstrates import, chapter parsing, and queued synthesis.
        """

        let parser = DefaultTextParser()
        let chapters = parser.parseChapters(from: text).enumerated().map { index, item in
            Chapter(index: index, title: item.title, rawText: item.text)
        }

        let book = Audiobook(title: "Sample Book", author: "Open Source", sourceType: .pasted, chapters: chapters)
        chapters.forEach { $0.book = book }

        try? repository.saveBook(book)
    }
}
