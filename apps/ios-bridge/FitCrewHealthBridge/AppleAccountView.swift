import SwiftUI
import AuthenticationServices
import FitCrewHealthCore

struct AppleAccountView: View {
    @ObservedObject var model: BridgeViewModel
    @State private var challenge: AppleChallenge?
    @State private var challengeIdentity: AccountIdentitySnapshot?
    @State private var message: String?
    @State private var busy = false

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            if let baseURL = Self.baseURL, let policyURL = ReleaseConfiguration.privacyPolicyURL {
                Text("使用 Apple 账号建立私人账号。继续表示同意隐私政策 2026-09-07；健康读取需要单独授权。")
                Link("阅读完整隐私政策", destination: policyURL).frame(minHeight: 44)
                if let challenge, let loginIdentity = challengeIdentity {
                    SignInWithAppleButton(.signIn) { request in
                        request.requestedScopes = []
                        request.nonce = challenge.nonce
                    } onCompletion: { result in
                        Task {
                            busy = true
                            defer { busy = false; self.challenge = nil }
                            do {
                                guard loginIdentity.isCurrent() else { return }
                                let authorization = try result.get()
                                guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
                                      let token = credential.identityToken.flatMap({ String(data: $0, encoding: .utf8) }),
                                      let code = credential.authorizationCode.flatMap({ String(data: $0, encoding: .utf8) }) else { throw URLError(.userAuthenticationRequired) }
                                let data = try await accountRequest(baseURL: baseURL, path: "/v3/auth/apple", body: ["challenge_id": challenge.challenge_id, "identity_token": token, "authorization_code": code, "privacy_version": "2026-09-07"])
                                guard loginIdentity.isCurrent() else { return }
                                try model.install(JSONDecoder().decode(PairingProvisioning.self, from: data))
                                message = nil
                            } catch { if loginIdentity.isCurrent() { message = "登录未完成，请重试。\(error.localizedDescription)" } }
                        }
                    }.frame(height: 50).disabled(busy)
                } else {
                    Button("使用 Apple 登录") {
                        let loginIdentity = AccountIdentitySnapshot()
                        Task {
                        busy = true
                        defer { busy = false }
                        do {
                            guard loginIdentity.isCurrent() else { return }
                            let result = try JSONDecoder().decode(AppleChallenge.self, from: await accountRequest(baseURL: baseURL, path: "/v3/auth/apple/challenge", body: [:]))
                            guard loginIdentity.isCurrent() else { return }
                            challengeIdentity = loginIdentity
                            challenge = result
                            message = nil
                        }
                        catch { if loginIdentity.isCurrent() { message = "暂时无法开始登录，请稍后重试。" } }
                    } }.frame(minHeight: 44).disabled(busy)
                }
            } else {
                Text(ReleaseConfiguration.privacyPolicyURL == nil ? "公开隐私政策尚未配置，Apple 正式登录暂不可用。" : "公开登录尚未配置服务地址，暂不可用。可以使用已有的邀请配对链接。").font(.footnote)
                Button("使用 Apple 登录") {}.disabled(true).frame(minHeight: 44)
            }
            if busy { ProgressView() }
            if let message { Text(message).foregroundStyle(.red) }
        }
    }

    private static var baseURL: URL? {
        guard let value = Bundle.main.object(forInfoDictionaryKey: "FitCrewAPIBaseURL") as? String,
              let url = URL(string: value), url.scheme == "https", url.host != nil else { return nil }
        return url
    }
}

private struct AppleChallenge: Decodable { let challenge_id, nonce: String }

enum ReleaseConfiguration {
    static var privacyPolicyURL: URL? { httpsURL(Bundle.main.object(forInfoDictionaryKey: "PrivacyPolicyURL") as? String) }
    static func httpsURL(_ value: String?) -> URL? {
        guard let value, let url = URL(string: value), url.scheme == "https", let host = url.host, !host.isEmpty,
              url.user == nil, url.password == nil else { return nil }
        return url
    }
}

private func accountRequest(baseURL: URL, path: String, body: [String: Any], token: String? = nil) async throws -> Data {
    var request = URLRequest(url: baseURL.appending(path: path))
    request.httpMethod = "POST"
    request.timeoutInterval = 30
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    if let token { request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
    request.httpBody = try JSONSerialization.data(withJSONObject: body)
    let (data, response) = try await URLSession.shared.data(for: request)
    guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else { throw URLError(.badServerResponse) }
    return data
}

struct HealthConsentView: View {
    @ObservedObject var model: BridgeViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var selected = Set<String>()
    @State private var message: String?
    @State private var busy = false
    private let scopes = [("blood_glucose", "血糖"), ("sleep_asleep", "总睡眠"), ("sleep_core", "核心睡眠"), ("sleep_deep", "深度睡眠"), ("sleep_rem", "快速眼动睡眠"), ("heart_rate_variability", "心率变异性"), ("resting_heart_rate", "静息心率"), ("step_count", "步数"), ("active_energy", "活动能量"), ("stand_hours", "站立时间"), ("workout", "训练")]
    var body: some View {
        NavigationStack { Form {
            Section("选择允许同步的数据") {
                Text("所选数据将加密上传到你的私人账号，用于生活方式观察和实验评价，不会自动进入群聊。随后可在 Apple 健康中选择具体读取权限。")
                ForEach(scopes, id: \.0) { key, label in Toggle(label, isOn: Binding(get: { selected.contains(key) }, set: { if $0 { selected.insert(key) } else { selected.remove(key) } })) }
            }
            Section {
                Button(selected.isEmpty ? "撤回全部上传授权" : "同意所选范围并继续") { Task {
                    busy = true
                    defer { busy = false }
                    do {
                        guard let configuration = ConsentStore().configuration, let token = KeychainStore.deviceToken() else { throw URLError(.userAuthenticationRequired) }
                        let identity = AccountIdentitySnapshot()
                        let data = try await accountRequest(baseURL: configuration.baseURL, path: "/v3/consents", body: ["categories": Array(selected).sorted(), "privacy_version": "2026-09-07"], token: token)
                        guard identity.isCurrent(), ConsentStore().configuration?.deviceBindingID == configuration.deviceBindingID,
                              ConsentStore().configuration?.baseURL == configuration.baseURL else { return }
                        let response = try JSONDecoder().decode(ConsentResponse.self, from: data)
                        ConsentStore().configuration = BridgeConfiguration(baseURL: configuration.baseURL, deviceBindingID: configuration.deviceBindingID, consentIDs: response.consent_ids)
                        if selected.isEmpty { model.refreshSyncState() }
                        else { await model.requestAuthorization() }
                        dismiss()
                    } catch { message = "授权未完成，请重试。\(error.localizedDescription)" }
                } }.disabled(busy)
                if let message { Text(message).foregroundStyle(.red) }
            }
        }.navigationTitle("健康数据授权").toolbar { Button("取消") { dismiss() } }
        .onAppear { selected = Set(ConsentStore().configuration?.consentIDs.keys.map { $0 } ?? []) } }
    }
}
private struct ConsentResponse: Decodable { let consent_ids: [String: UUID] }
