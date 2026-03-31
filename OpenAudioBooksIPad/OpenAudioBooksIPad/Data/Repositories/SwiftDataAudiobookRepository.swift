import Foundation
import SwiftData

@MainActor
final class SwiftDataAudiobookRepository: AudiobookRepository {
    private let context: ModelContext

    init(context: ModelContext) {
        self.context = context
    }

    func fetchBooks(search: String?) throws -> [Audiobook] {
        var descriptor = FetchDescriptor<Audiobook>(sortBy: [SortDescriptor(\Audiobook.updatedAt, order: .reverse)])
        if let search, !search.isEmpty {
            descriptor.predicate = #Predicate<Audiobook> { book in
                book.title.localizedStandardContains(search)
            }
        }
        return try context.fetch(descriptor)
    }

    func fetchBook(id: UUID) throws -> Audiobook? {
        let descriptor = FetchDescriptor<Audiobook>(predicate: #Predicate { $0.id == id })
        return try context.fetch(descriptor).first
    }

    func saveBook(_ book: Audiobook) throws {
        book.updatedAt = .now
        if book.modelContext == nil {
            context.insert(book)
        }
        try context.save()
    }

    func savePlayback(_ state: PlaybackState, for book: Audiobook) throws {
        state.book = book
        context.insert(state)
        try context.save()
    }

    func playbackState(for book: Audiobook) throws -> PlaybackState? {
        let descriptor = FetchDescriptor<PlaybackState>(predicate: #Predicate { $0.book?.id == book.id })
        return try context.fetch(descriptor).first
    }
}
