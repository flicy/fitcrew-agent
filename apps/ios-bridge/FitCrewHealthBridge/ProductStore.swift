import Foundation
import FitCrewHealthCore

@MainActor
final class ProductStore: ObservableObject {
    @Published private(set) var state: ProductState?
    @Published private(set) var busy = false
    @Published var error: String?
    @Published var receipt: String?
    @Published var exportURL: URL?
    @Published private(set) var capabilities: ProductCapabilities?
    @Published private(set) var requiresReauthentication = false
    private var pendingRequestIDs: [String: String] = [:]
    private var identityRevision: UUID?
    private var activeOperation: UUID?
    private let revisionProvider: () -> UUID
    private let configurationProvider: () -> BridgeConfiguration?
    private let tokenProvider: () -> String?
    private let transport: (URLRequest) async throws -> (Data, URLResponse)
    private let exportDirectory: URL

    init(
        revisionProvider: @escaping () -> UUID = { ConsentStore().identityRevision },
        configurationProvider: @escaping () -> BridgeConfiguration? = { ConsentStore().configuration },
        tokenProvider: @escaping () -> String? = { KeychainStore.deviceToken() },
        exportDirectory: URL = FileManager.default.temporaryDirectory,
        transport: @escaping (URLRequest) async throws -> (Data, URLResponse) = { try await URLSession.shared.data(for: $0) }
    ) {
        self.revisionProvider = revisionProvider
        self.configurationProvider = configurationProvider
        self.tokenProvider = tokenProvider
        self.exportDirectory = exportDirectory
        self.transport = transport
        synchronizeIdentity()
    }

    private func clearExports() {
        let files = (try? FileManager.default.contentsOfDirectory(at: exportDirectory, includingPropertiesForKeys: nil)) ?? []
        for url in files where url.lastPathComponent.hasPrefix("FitCrew-export-") && url.pathExtension == "json" {
            try? FileManager.default.removeItem(at: url)
        }
        exportURL = nil
    }

    func synchronizeIdentity() {
        let revision = revisionProvider()
        guard identityRevision != revision else { return }
        identityRevision = revision
        activeOperation = nil
        busy = false
        state = nil
        capabilities = nil
        receipt = nil
        error = nil
        requiresReauthentication = false
        pendingRequestIDs.removeAll()
        clearExports()
    }

    private func beginOperation() -> UUID? {
        synchronizeIdentity()
        guard !busy else { return nil }
        let operation = UUID()
        activeOperation = operation
        busy = true
        return operation
    }

    private func isCurrent(_ operation: UUID) -> Bool {
        activeOperation == operation && identityRevision == revisionProvider()
    }

    private func finish(_ operation: UUID) {
        if activeOperation == operation { activeOperation = nil; busy = false }
    }

    private func request(_ path: String, operation: UUID, method: String = "GET", body: [String: Any]? = nil) async throws -> Data {
        guard isCurrent(operation) else { throw CancellationError() }
        guard let configuration = configurationProvider(), let token = tokenProvider() else {
            throw ProductError.message("请先在我的页面连接账号。")
        }
        var request = URLRequest(url: configuration.baseURL.appending(path: path))
        request.httpMethod = method
        request.timeoutInterval = 30
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        if let body {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let (data, response) = try await transport(request)
        guard isCurrent(operation), configurationProvider()?.deviceBindingID == configuration.deviceBindingID,
              configurationProvider()?.baseURL == configuration.baseURL else { throw CancellationError() }
        guard let http = response as? HTTPURLResponse else { throw URLError(.badServerResponse) }
        guard (200..<300).contains(http.statusCode) else {
            switch http.statusCode {
            case 401:
                requiresReauthentication = true
                state = nil
                capabilities = nil
                throw ProductError.message("连接已过期，请在我的页面重新登录。未提交的输入仍保留。")
            case 403: throw ProductError.message("当前操作权限不足，请检查授权范围。")
            case 409: throw ProductError.message("状态已更新，请刷新后重试。你的输入仍然保留。")
            default: throw ProductError.message("服务暂时不可用（\(http.statusCode)）。请稍后重试。")
            }
        }
        requiresReauthentication = false
        return data
    }

    func refresh() async {
        guard let operation = beginOperation() else { return }
        defer { finish(operation) }
        do {
            let newState = try ProductState.decode(await request("/v3/state", operation: operation))
            let newCapabilities = try JSONDecoder().decode(ProductCapabilities.self, from: await request("/v3/capabilities", operation: operation))
            guard isCurrent(operation) else { return }
            state = newState
            capabilities = newCapabilities
            error = nil
        }
        catch { if isCurrent(operation) { self.error = error.localizedDescription } }
    }

    @discardableResult
    func mutate(_ path: String, method: String = "POST", body: [String: Any] = [:]) async -> Bool {
        guard let operation = beginOperation() else { return false }
        defer { finish(operation) }
        do {
            var payload = body
            let bodyData = try JSONSerialization.data(withJSONObject: body, options: .sortedKeys)
            let operationKey = method + path + bodyData.base64EncodedString()
            let requestID = pendingRequestIDs[operationKey] ?? UUID().uuidString
            pendingRequestIDs[operationKey] = requestID
            if path != "/v3/ai-consent" { payload["request_id"] = requestID }
            _ = try await request(path, operation: operation, method: method, body: payload)
            guard isCurrent(operation) else { return false }
            pendingRequestIDs.removeValue(forKey: operationKey)
            // A successful mutation is acknowledged even if the following refresh fails.
            do {
                let newState = try ProductState.decode(await request("/v3/state", operation: operation))
                let newCapabilities = try JSONDecoder().decode(ProductCapabilities.self, from: await request("/v3/capabilities", operation: operation))
                guard isCurrent(operation) else { return false }
                state = newState
                capabilities = newCapabilities
                error = nil
            }
            catch { guard isCurrent(operation) else { return false }; self.error = "已保存，但刷新失败，请下拉刷新。" }
            return true
        } catch { if isCurrent(operation) { self.error = error.localizedDescription }; return false }
    }

    func exportData() async {
        guard let operation = beginOperation() else { return }
        defer { finish(operation) }
        do {
            let data = try await request("/v3/export", operation: operation)
            guard isCurrent(operation) else { return }
            clearExports()
            let url = exportDirectory.appending(path: "FitCrew-export-\(UUID().uuidString).json")
            try data.write(to: url, options: [.atomic, .completeFileProtection])
            exportURL = url
        } catch { if isCurrent(operation) { self.error = error.localizedDescription } }
    }

    @discardableResult
    func delete(_ kind: String) async -> Bool {
        guard let operation = beginOperation() else { return false }
        defer { finish(operation) }
        do {
            let data = try await request("/v3/\(kind)", operation: operation, method: "DELETE", body: ["confirmation": "DELETE"])
            guard isCurrent(operation) else { return false }
            let result = try JSONDecoder().decode(DeletionReceipt.self, from: data)
            guard result.deleted else { throw ProductError.message("服务器未确认删除，请重试。") }
            receipt = result.receipt_id
            state = nil
            capabilities = nil
            clearExports()
            if let old = ConsentStore().configuration {
                ConsentStore().configuration = BridgeConfiguration(baseURL: old.baseURL, deviceBindingID: old.deviceBindingID, consentIDs: [:])
                ConsentStore().lastSync = nil
                ConsentStore().lastFullReconciliation = nil
            }
            if kind == "account" { ConsentStore().configuration = nil; KeychainStore.removeDeviceToken() }
            identityRevision = revisionProvider()
            error = nil
            pendingRequestIDs.removeAll()
            return true
        } catch { if isCurrent(operation) { self.error = error.localizedDescription }; return false }
    }
}

private struct DeletionReceipt: Decodable { let deleted: Bool; let receipt_id: String }
struct ProductCapabilities: Decodable {
    let ai_available: Bool
    let ai_provider: String
    let ai_notice: String
    let ai_notice_version: String
    let ai_consent_granted: Bool
}
private enum ProductError: LocalizedError {
    case message(String)
    var errorDescription: String? { if case .message(let text) = self { return text }; return nil }
}
