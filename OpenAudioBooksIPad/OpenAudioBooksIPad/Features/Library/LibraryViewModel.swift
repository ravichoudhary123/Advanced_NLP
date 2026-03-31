import Foundation

@MainActor
final class LibraryViewModel: ObservableObject {
    @Published var books: [Audiobook] = []
    @Published var searchText: String = ""
    @Published var selectedBook: Audiobook?
    @Published var errorMessage: String?

    private let repository: AudiobookRepository
    private let queueService: TTSQueueService

    init(repository: AudiobookRepository, queueService: TTSQueueService) {
        self.repository = repository
        self.queueService = queueService
        refresh()
    }

    func refresh() {
        do {
            books = try repository.fetchBooks(search: searchText)
            if selectedBook == nil {
                selectedBook = books.first
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func generateAudio(for book: Audiobook, voice: VoiceProfile, chunkSize: Int) {
        Task {
            await queueService.enqueueGeneration(for: book, voice: voice, chunkSize: chunkSize)
            refresh()
        }
    }
}
