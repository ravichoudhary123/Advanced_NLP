import SwiftUI

struct LibraryView: View {
    @ObservedObject var viewModel: LibraryViewModel

    private let columns = [GridItem(.adaptive(minimum: 220, maximum: 280), spacing: 16)]

    var body: some View {
        List(selection: $viewModel.selectedBook) {
            if viewModel.books.isEmpty {
                ContentUnavailableView("No Audiobooks", systemImage: "book.closed", description: Text("Import TXT/PDF or paste text to get started."))
            } else {
                ForEach(viewModel.books) { book in
                    VStack(alignment: .leading, spacing: 6) {
                        Text(book.title)
                            .font(.headline)
                        Text(book.author ?? "Unknown Author")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Text(book.status.rawValue.capitalized)
                            .font(.caption)
                            .padding(4)
                            .background(.thinMaterial)
                            .clipShape(RoundedRectangle(cornerRadius: 6))
                    }
                    .tag(book)
                }
            }
        }
        .navigationTitle("Library")
        .searchable(text: $viewModel.searchText)
        .onChange(of: viewModel.searchText) { _, _ in viewModel.refresh() }
        .toolbar {
            NavigationLink {
                ImportView()
            } label: {
                Label("Import", systemImage: "square.and.arrow.down")
            }

            NavigationLink {
                SettingsView()
            } label: {
                Label("Settings", systemImage: "gear")
            }
        }
    }
}
