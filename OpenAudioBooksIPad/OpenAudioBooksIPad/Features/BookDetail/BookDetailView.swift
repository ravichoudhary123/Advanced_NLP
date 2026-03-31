import SwiftUI

struct BookDetailView: View {
    @EnvironmentObject private var libraryVM: LibraryViewModel
    @EnvironmentObject private var settingsVM: SettingsViewModel
    @EnvironmentObject private var playerVM: PlayerViewModel

    let book: Audiobook

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(book.title)
                .font(.largeTitle)
            Text("Status: \(book.status.rawValue.capitalized)")
                .foregroundStyle(.secondary)

            HStack {
                Button("Generate Audio") {
                    libraryVM.generateAudio(for: book, voice: settingsVM.selectedVoice, chunkSize: settingsVM.settings.chunkSize)
                }
                .buttonStyle(.borderedProminent)

                Button("Open Player") {
                    playerVM.present(book: book)
                }
                .buttonStyle(.bordered)
            }

            List {
                ForEach(book.chapters.sorted(by: { $0.index < $1.index })) { chapter in
                    HStack {
                        VStack(alignment: .leading) {
                            Text(chapter.title)
                            Text(chapter.status.rawValue.capitalized)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button("Regenerate") {
                            libraryVM.generateAudio(for: book, voice: settingsVM.selectedVoice, chunkSize: settingsVM.settings.chunkSize)
                        }
                    }
                }
            }
        }
        .padding()
    }
}
