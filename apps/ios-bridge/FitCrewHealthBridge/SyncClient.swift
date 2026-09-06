import FitCrewHealthCore
import Foundation

struct SyncClient {
    let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    func upload(
        _ batch: HealthSyncBatchDTO,
        to baseURL: URL,
        deviceToken: String
    ) async throws {
        var request = URLRequest(url: baseURL.appending(path: "/v1/health/sync"))
        request.httpMethod = "POST"
        request.httpBody = try JSONEncoder.fitCrew.encode(batch)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(deviceToken)", forHTTPHeaderField: "Authorization")
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, 200..<300 ~= http.statusCode else {
            throw URLError(.badServerResponse)
        }
    }

    fileprivate func exchange(_ invitation: PairingInvitation) async throws -> PairingProvisioning {
        var request = URLRequest(url: invitation.baseURL.appending(path: "/v1/pairing/exchange"))
        request.httpMethod = "POST"
        request.setValue("Bearer \(invitation.pairingCode)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, 200..<300 ~= http.statusCode else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(PairingProvisioning.self, from: data)
    }
}

struct PairingProvisioning: Decodable {
    let baseURL: URL
    let deviceBindingID: UUID
    let consentIDs: [String: UUID]
    let deviceToken: String

    enum CodingKeys: String, CodingKey {
        case baseURL = "base_url"
        case deviceBindingID = "device_binding_id"
        case consentIDs = "consent_ids"
        case deviceToken = "device_token"
    }
}

@MainActor
final class BridgeViewModel: ObservableObject {
    @Published private(set) var statusMessage = "等待授权"
    @Published private(set) var authorizationStatus = "未确认"
    @Published private(set) var lastSync: Date?
    @Published private(set) var isSyncing = false
    @Published private(set) var identityRevision: UUID

    private let healthKit = HealthKitClient()
    private let syncClient = SyncClient()
    private let consentStore = ConsentStore()

    init() {
        identityRevision = consentStore.identityRevision
        lastSync = consentStore.lastSync
    }

    var isConfigured: Bool {
        consentStore.configuration != nil && KeychainStore.deviceToken() != nil
    }

    var lastSyncText: String {
        guard let lastSync else { return "尚未同步" }
        return lastSync.formatted(date: .abbreviated, time: .shortened)
    }

    func refreshSyncState() {
        identityRevision = consentStore.identityRevision
        lastSync = consentStore.lastSync
        if consentStore.configuration?.consentIDs.isEmpty != false {
            authorizationStatus = "尚未授权上传健康数据"
            statusMessage = "健康同步已停止，需重新选择授权范围"
        }
    }

    func configure(from url: URL) async {
        do {
            let invitation = try PairingDecoder.decode(url)
            let pairing = try await syncClient.exchange(invitation)
            guard pairing.baseURL.scheme == "https", pairing.baseURL.host != nil else {
                throw PairingError.invalidPayload
            }
            try KeychainStore.saveDeviceToken(pairing.deviceToken)
            consentStore.replaceConfiguration(BridgeConfiguration(
                baseURL: pairing.baseURL,
                deviceBindingID: pairing.deviceBindingID,
                consentIDs: pairing.consentIDs
            ))
            lastSync = consentStore.lastSync
            identityRevision = consentStore.identityRevision
            statusMessage = "设备绑定成功，请授权 Apple 健康"
        } catch {
            statusMessage = "设备绑定失败：\(error.localizedDescription)"
        }
    }

    func requestAuthorization() async {
        let identity = AccountIdentitySnapshot(store: consentStore)
        let configuration = consentStore.configuration
        do {
            let kinds = Set(consentStore.configuration?.consentIDs.keys.map { $0 } ?? [])
            guard !kinds.isEmpty else { statusMessage = "请先选择健康数据授权范围"; return }
            try await healthKit.requestAuthorization(kinds: kinds)
            guard identity.isCurrent(in: consentStore), consentStore.configuration == configuration else { return }
            authorizationStatus = "已请求最小读取权限"
            statusMessage = "授权完成后可以同步"
        } catch {
            if identity.isCurrent(in: consentStore), consentStore.configuration == configuration {
                statusMessage = "授权失败：\(error.localizedDescription)"
            }
        }
    }

    func install(_ pairing: PairingProvisioning) throws {
        guard pairing.baseURL.scheme == "https", pairing.baseURL.host != nil else { throw PairingError.invalidPayload }
        try KeychainStore.saveDeviceToken(pairing.deviceToken)
        consentStore.replaceConfiguration(BridgeConfiguration(baseURL: pairing.baseURL, deviceBindingID: pairing.deviceBindingID, consentIDs: pairing.consentIDs))
        lastSync = consentStore.lastSync
        identityRevision = consentStore.identityRevision
        statusMessage = "账号已连接，Apple 健康授权可选"
    }

    @discardableResult
    func sync(fullReconciliation: Bool) async -> Bool {
        guard !isSyncing else { return false }
        isSyncing = true
        defer { isSyncing = false }
        guard let configuration = consentStore.configuration,
              let token = KeychainStore.deviceToken(), !configuration.consentIDs.isEmpty
        else {
            statusMessage = "请先完成设备绑定"
            return false
        }
        let endDate = Date()
        let identity = AccountIdentitySnapshot(store: consentStore)
        let startDate = fullReconciliation
            ? Calendar.current.date(byAdding: .day, value: -30, to: endDate)!
            : (lastSync ?? Calendar.current.date(byAdding: .day, value: -1, to: endDate)!)
        do {
            let samples = try await healthKit.readSamples(since: startDate, until: endDate, kinds: Set(configuration.consentIDs.keys))
                .filter { configuration.consentIDs[$0.kind.rawValue] != nil }
            guard identity.isCurrent(in: consentStore), consentStore.configuration == configuration else { return false }
            let batches = try BatchPlanner.makeBatches(
                deviceBindingID: configuration.deviceBindingID,
                consentIDs: configuration.consentIDs,
                cursor: startDate.ISO8601Format(),
                source: "apple-healthkit",
                timezone: TimeZone.current.identifier,
                sentAt: endDate,
                fullReconciliation: fullReconciliation,
                samples: samples
            )
            for batch in batches {
                guard identity.isCurrent(in: consentStore), consentStore.configuration == configuration else { return false }
                try await syncClient.upload(batch, to: configuration.baseURL, deviceToken: token)
            }
            guard identity.isCurrent(in: consentStore), consentStore.configuration == configuration else { return false }
            lastSync = endDate
            consentStore.lastSync = endDate
            if fullReconciliation {
                consentStore.lastFullReconciliation = endDate
            }
            statusMessage = "同步成功，共处理 \(samples.count) 条样本"
            BackgroundSyncScheduler.shared.schedule()
            return true
        } catch {
            if identity.isCurrent(in: consentStore), consentStore.configuration == configuration {
                statusMessage = "同步失败，游标未推进：\(error.localizedDescription)"
            }
            return false
        }
    }

    var requiresFullReconciliation: Bool {
        guard let studyStart = consentStore.studyStart else { return false }
        return StudySchedule.requiresFullReconciliation(
            startedAt: studyStart,
            lastFullReconciliation: consentStore.lastFullReconciliation,
            now: Date()
        )
    }
}
