import SwiftUI

struct ZScoreCalculatorView: View {
    @State private var vix3M: [String] = Array(repeating: "", count: 10)
    @State private var vix1M: [String] = Array(repeating: "", count: 10)
    @State private var usePopulationStd = false

    private var diffs: [Double?] {
        zip(vix3M, vix1M).map { vix3, vix1 in
            guard let v3 = Double(vix3), let v1 = Double(vix1) else {
                return nil
            }
            return v3 - v1
        }
    }

    private var mean: Double? {
        let values = diffs.compactMap { $0 }
        guard values.count == 10 else { return nil }
        return values.reduce(0, +) / Double(values.count)
    }

    private var std: Double? {
        let values = diffs.compactMap { $0 }
        guard let mean, values.count == 10 else { return nil }
        let denominator = usePopulationStd ? Double(values.count) : Double(values.count - 1)
        let variance = values.reduce(0) { $0 + pow($1 - mean, 2) } / denominator
        return sqrt(variance)
    }

    private var zScore: Double? {
        guard let mean, let std, std > 0, let latest = diffs.first ?? nil else { return nil }
        return (latest - mean) / std
    }

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("一、滚动 10 日 z-score 是如何精确计算的？")
                            .font(.headline)
                            .foregroundColor(.blue)
                        Text("滚动 10 日 z-score 计算器")
                            .font(.title)
                            .bold()
                        Text("输入最近 10 天的 VIX3M 与 VIX1M，计算每日期限结构价差，以及 10 日滚动均值、标准差与 z-score。")
                            .foregroundColor(.secondary)
                    }

                    formulaCard

                    Toggle(isOn: $usePopulationStd) {
                        Text(usePopulationStd ? "总体标准差（1/10）" : "样本标准差（1/9，STDEV.S）")
                            .fontWeight(.semibold)
                    }
                    .toggleStyle(SwitchToggleStyle(tint: .blue))

                    inputTable

                    resultsCard

                    explanationCard
                }
                .padding()
            }
            .navigationTitle("z-score 计算器")
        }
    }

    private var formulaCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("定义每日期限结构价差")
                .font(.headline)
            Text("dₜ = VIX3Mₜ − VIX1Mₜ")
                .font(.title3)

            Text("计算 10 日滚动均值与标准差")
                .font(.headline)
            Text("μₜ = (1/10) Σᵢ₌₀⁹ dₜ₋ᵢ")
            Text("sₜ = √( (1/9) Σᵢ₌₀⁹ (dₜ₋ᵢ − μₜ)² )")

            Text("最终得到 z-score")
                .font(.headline)
            Text("zₜ = (dₜ − μₜ) / sₜ")
                .font(.title3)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(radius: 4, x: 0, y: 2)
    }

    private var inputTable: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("最近 10 天输入")
                .font(.headline)
            ForEach(0..<10, id: \.self) { index in
                HStack(spacing: 12) {
                    Text("第 \(10 - index) 天")
                        .frame(width: 80, alignment: .leading)
                    TextField("VIX3M", text: $vix3M[index])
                        .keyboardType(.decimalPad)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                    TextField("VIX1M", text: $vix1M[index])
                        .keyboardType(.decimalPad)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                    Text(diffText(for: index))
                        .frame(width: 80, alignment: .trailing)
                        .foregroundColor(.blue)
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(radius: 4, x: 0, y: 2)
    }

    private func diffText(for index: Int) -> String {
        guard let diff = diffs[index] else { return "—" }
        return String(format: "%.4f", diff)
    }

    private var resultsCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("结果")
                .font(.headline)
            HStack {
                resultBlock(title: "滚动均值 μₜ", value: mean)
                resultBlock(title: "滚动标准差 sₜ", value: std)
                resultBlock(title: "z-score zₜ", value: zScore)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(radius: 4, x: 0, y: 2)
    }

    private func resultBlock(title: String, value: Double?) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.subheadline)
                .foregroundColor(.secondary)
            Text(formatted(value))
                .font(.title3)
                .fontWeight(.bold)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func formatted(_ value: Double?) -> String {
        guard let value else { return "—" }
        return String(format: "%.4f", value)
    }

    private var explanationCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("解释")
                .font(.headline)
            Text("• 使用 1/9 是常见的样本标准差做法（Excel 的 STDEV.S）。")
            Text("• 有些人用 1/10（总体标准差），只要前后一致即可。")
            Text("• 例如：zₜ = −2 表示当前期限价差比最近 10 日均值低 2 个标准差。")
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(radius: 4, x: 0, y: 2)
    }
}

@main
struct ZScoreCalculatorApp: App {
    var body: some Scene {
        WindowGroup {
            ZScoreCalculatorView()
        }
    }
}
