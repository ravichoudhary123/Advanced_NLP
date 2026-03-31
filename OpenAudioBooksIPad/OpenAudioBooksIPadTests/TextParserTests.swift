import XCTest
@testable import OpenAudioBooksIPad

final class TextParserTests: XCTestCase {
    func testChapterParsingDetectsHeadings() {
        let parser = DefaultTextParser()
        let text = "Chapter 1\nHello\n\nChapter 2\nWorld"
        let chapters = parser.parseChapters(from: text)
        XCTAssertEqual(chapters.count, 2)
    }

    func testChunkingRespectsTargetSize() {
        let parser = DefaultTextParser()
        let text = Array(repeating: "word", count: 200).joined(separator: " ")
        let chunks = parser.chunk(chapterText: text, targetSize: 100)
        XCTAssertGreaterThan(chunks.count, 1)
    }
}
