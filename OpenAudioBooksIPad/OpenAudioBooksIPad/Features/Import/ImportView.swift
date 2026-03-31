import SwiftUI
import UniformTypeIdentifiers

struct ImportView: View {
    @Environment(\.container) private var container

    @State private var pastedText: String = ""
    @State private var title: String = "Pasted Book"
    @State private var errorMessage: String?
    @State private var showingFileImporter = false

    var body: some View {
        Form {
            Section("Import from Files") {
                Button("Choose TXT/PDF/EPUB") {
                    showingFileImporter = true
                }
            }

            Section("Paste text") {
                TextField("Title", text: $title)
                TextEditor(text: $pastedText)
                    .frame(minHeight: 220)
                Button("Create Book") {
                    importPastedText()
                }
            }

            if let errorMessage {
                Section("Error") {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                }
            }
        }
        .navigationTitle("Import")
        .fileImporter(
            isPresented: $showingFileImporter,
            allowedContentTypes: [.plainText, .pdf, UTType(filenameExtension: "epub") ?? .data]
        ) { result in
            if case let .success(url) = result {
                importFile(url)
            }
        }
    }

    private func importPastedText() {
        do {
            let book = try container.importService.importText(pastedText, suggestedTitle: title)
            try container.audiobookRepository.saveBook(book)
            pastedText = ""
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func importFile(_ url: URL) {
        do {
            let book = try container.importService.importFile(at: url)
            try container.audiobookRepository.saveBook(book)
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
