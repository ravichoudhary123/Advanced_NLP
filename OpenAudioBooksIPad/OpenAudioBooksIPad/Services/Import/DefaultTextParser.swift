import Foundation

struct ParsedChapter {
    let title: String
    let text: String
}

struct TextChunk {
    let index: Int
    let text: String
    let start: Int
    let end: Int
}

struct DefaultTextParser {
    func parseChapters(from text: String) -> [ParsedChapter] {
        let normalized = text.replacingOccurrences(of: "\r\n", with: "\n")
        let sections = normalized.components(separatedBy: "\n\n")

        var chapters: [ParsedChapter] = []
        var buffer: [String] = []
        var chapterIndex = 1

        for section in sections {
            let trimmed = section.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty else { continue }

            if trimmed.lowercased().hasPrefix("chapter ") || trimmed.lowercased().hasPrefix("ch ") {
                if !buffer.isEmpty {
                    chapters.append(ParsedChapter(title: "Chapter \(chapterIndex)", text: buffer.joined(separator: "\n\n")))
                    buffer.removeAll()
                    chapterIndex += 1
                }
                buffer.append(trimmed)
            } else {
                buffer.append(trimmed)
            }
        }

        if !buffer.isEmpty {
            chapters.append(ParsedChapter(title: "Chapter \(chapterIndex)", text: buffer.joined(separator: "\n\n")))
        }

        if chapters.isEmpty {
            return [ParsedChapter(title: "Chapter 1", text: normalized)]
        }

        return chapters
    }

    func chunk(chapterText: String, targetSize: Int) -> [TextChunk] {
        let words = chapterText.split(separator: " ")
        guard !words.isEmpty else { return [] }

        var chunks: [TextChunk] = []
        var currentWords: [Substring] = []
        var currentCount = 0
        var charOffset = 0

        for word in words {
            let wordCount = word.count + 1
            if currentCount + wordCount > targetSize, !currentWords.isEmpty {
                let text = currentWords.joined(separator: " ")
                let end = charOffset + text.count
                chunks.append(TextChunk(index: chunks.count, text: String(text), start: charOffset, end: end))
                charOffset = end + 1
                currentWords.removeAll()
                currentCount = 0
            }

            currentWords.append(word)
            currentCount += wordCount
        }

        if !currentWords.isEmpty {
            let text = currentWords.joined(separator: " ")
            let end = charOffset + text.count
            chunks.append(TextChunk(index: chunks.count, text: String(text), start: charOffset, end: end))
        }

        return chunks
    }
}
