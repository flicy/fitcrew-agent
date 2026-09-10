import Foundation

struct AccountIdentitySnapshot: Equatable {
    let revision: UUID
    let bindingID: UUID?
    let baseURL: URL?

    init(store: ConsentStore = ConsentStore()) {
        revision = store.identityRevision
        bindingID = store.configuration?.deviceBindingID
        baseURL = store.configuration?.baseURL
    }

    func isCurrent(in store: ConsentStore = ConsentStore()) -> Bool {
        self == AccountIdentitySnapshot(store: store)
    }
}
