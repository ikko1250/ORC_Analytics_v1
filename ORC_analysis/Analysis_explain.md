# 有機ランキンサイクル (ORC) 性能解析モデル

このドキュメントは、指定されたPythonスクリプト `ORC_Analysis.py` に基づく有機ランキンサイクル (ORC) の性能解析モデルの計算ロジックを解説します。このモデルは、作動流体の熱力学状態の計算、主要コンポーネント（ポンプ、蒸発器、タービン、凝縮器）の性能分析、サイクル全体の主要業績評価指標 (KPI) の算出、蒸発器における対数平均温度差 (LMTD) の考慮、およびコンポーネントとサイクル全体のエクセルギー解析を含みます。

## 記号の定義

以下に、本解析で用いられる主要な記号とその単位を示します。

| 記号             | 説明                                     | 単位        |
| ---------------- | ---------------------------------------- | ----------- |
| $T$              | 温度                                     | K           |
| $P$              | 圧力                                     | Pa          |
| $h$              | 比エンタルピー                           | kJ/kg       |
| $s$              | 比エントロピー                           | kJ/(kg·K)   |
| $\psi$           | 比流れエクセルギー                       | kJ/kg       |
| $\dot{m}$        | 質量流量                                 | kg/s        |
| $\dot{Q}$        | 熱流量                                   | kW          |
| $\dot{W}$        | 仕事率 (動力)                            | kW          |
| $\eta$           | 効率                                     | -           |
| $\varepsilon$    | エクセルギー効率                         | -           |
| $T_0$            | 環境 (基準) 温度                         | K           |
| $P_0$            | 環境 (基準) 圧力                         | Pa          |
| $h_0$            | 環境状態における比エンタルピー           | kJ/kg       |
| $s_0$            | 環境状態における比エントロピー           | kJ/(kg·K)   |
| LMTD             | 対数平均温度差                           | K           |
| 下付き文字:      |                                          |             |
| `orc`            | ORC作動流体に関する量                    |             |
| `htf`            | 熱媒体 (Heat Transfer Fluid) に関する量    |             |
| `1, 2, 3, 4`     | ORCサイクル上の状態点                    |             |
| `s`              | 等エントロピー過程を示す (例: $h_{2s}$)  |             |
| `p`              | ポンプ                                   |             |
| `t`              | タービン                                 |             |
| `e`              | 蒸発器                                   |             |
| `c`              | 凝縮器                                   |             |
| `in`             | 入口                                       |             |
| `out`            | 出口                                       |             |
| `rev`            | 可逆過程                                 |             |
| `dest`           | 破壊された (destroyed)                   |             |
| `th`             | 熱効率 (thermal)                         |             |
| `ex`             | エクセルギー効率 (exergetic)             |             |

## 1. 基本的な熱力学関数

### 1.1 対数平均温度差 (LMTD)

対向流熱交換器における対数平均温度差 (LMTD) は、熱交換器の性能評価に用いられます。高温流体の入口温度を $T_{hot,in}$、出口温度を $T_{hot,out}$、低温流体の入口温度を $T_{cold,in}$、出口温度を $T_{cold,out}$ とすると、LMTDは次のように定義されます。

$\Delta T_1 = T_{hot,in} - T_{cold,out}$
$\Delta T_2 = T_{hot,out} - T_{cold,in}$

もし $|\Delta T_1 - \Delta T_2| < 10^{-9}$ の場合 (つまり $\Delta T_1 \approx \Delta T_2$):
$\text{LMTD} = \Delta T_1$

それ以外の場合:
$\text{LMTD} = \frac{\Delta T_1 - \Delta T_2}{\ln(\Delta T_1 / \Delta T_2)}$

### 1.2 比流れエクセルギー

流れ系の定常状態における比物理エクセルギー $\psi$ は、環境状態 ($h_0, s_0, T_0$) を基準として次のように計算されます。

$\psi = (h - h_0) - T_0 (s - s_0)$

ここで、$h$ は比エンタルピー、$s$ は比エントロピー、$T_0$ は環境温度です。

### 1.3 熱のエクセルギー

温度 $T_{surf}$ の熱源表面から供給される熱量 $\dot{Q}$ のエクセルギー率 $\dot{E}_Q$ は、次のように計算されます。

$\dot{E}_Q = \left(1 - \frac{T_0}{T_{surf}}\right) \dot{Q}$

ただし、$T_{surf} > 0$ かつ $\dot{Q} \neq 0$ の場合に適用されます。それ以外の場合は $\dot{E}_Q = 0$ となります。

## 2. 熱力学物性値の取得

作動流体および熱媒体の熱力学物性値 (エンタルピー、エントロピー、温度、圧力、密度、比熱など) は、CoolPropライブラリの `PropsSI` 関数を介して取得されます。スクリプト内の `_get_coolprop_property` 関数は、この `PropsSI` 関数のラッパーとして機能し、指定された2つの独立な状態量から目的の物性値を計算します。

## 3. ORCサイクルの状態点計算

ORCの性能解析は、サイクル上の主要な状態点における熱力学状態量を決定することから始まります。

### 3.1 環境基準状態

エクセルギー計算の基準となる環境状態は、温度 $T_0$ および圧力 $P_0$ で定義されます。この状態における作動流体の比エンタルピー $h_0$ および比エントロピー $s_0$ が計算されます。

$h_0 = \text{PropsSI}("H", "T", T_0, "P", P_0, \text{fluid}) / 1000 \quad [\text{kJ/kg}]$
$s_0 = \text{PropsSI}("S", "T", T_0, "P", P_0, \text{fluid}) / 1000 \quad [\text{kJ/(kg*K)}]$

(スクリプトでは `J_PER_KJ` (1000) で除算しています)

### 3.2 状態点1 (凝縮器出口 / ポンプ入口)

状態点1は、凝縮器の出口であり、ポンプの入口です。作動流体は飽和液状態にあると仮定されます。

*   温度: $T_1 = T_{cond}$ (指定された凝縮温度)
*   圧力: $P_1 = \text{PropsSI}("P", "T", T_1, "Q", 0, \text{fluid})$ (凝縮温度における飽和液圧力)
*   比エンタルピー: $h_1 = \text{PropsSI}("H", "T", T_1, "Q", 0, \text{fluid}) / 1000$
*   比エントロピー: $s_1 = \text{PropsSI}("S", "T", T_1, "Q", 0, \text{fluid}) / 1000$

### 3.3 状態点2 (ポンプ出口 / 蒸発器入口)

状態点2は、ポンプの出口であり、蒸発器の入口です。ポンプによる昇圧過程を考えます。

*   圧力: $P_2 = P_{evap}$ (指定された蒸発圧力)
*   理想的なポンプ仕事 (等エントロピー過程):
    $s_{2s} = s_1$
    $h_{2s} = \text{PropsSI}("H", "P", P_2, "S", s_{2s} \times 1000, \text{fluid}) / 1000$
*   実際のポンプ出口エンタルピー (ポンプ効率 $\eta_{pump}$ を考慮):
    $h_2 = h_1 + \frac{h_{2s} - h_1}{\eta_{pump}}$
*   温度: $T_2 = \text{PropsSI}("T", "P", P_2, "H", h_2 \times 1000, \text{fluid})$
*   比エントロピー: $s_2 = \text{PropsSI}("S", "P", P_2, "H", h_2 \times 1000, \text{fluid}) / 1000$

### 3.4 状態点3 (蒸発器出口 / タービン入口)

状態点3は、蒸発器の出口であり、タービンの入口です。作動流体は過熱蒸気または飽和蒸気です。

*   温度: $T_3 = T_{turb,in}$ (指定されたタービン入口温度)
*   圧力: $P_3 = P_{evap}$ (指定された蒸発圧力)
*   比エンタルピー: $h_3 = \text{PropsSI}("H", "T", T_3, "P", P_3, \text{fluid}) / 1000$
*   比エントロピー: $s_3 = \text{PropsSI}("S", "T", T_3, "P", P_3, \text{fluid}) / 1000$

### 3.5 状態点4 (タービン出口 / 凝縮器入口)

状態点4は、タービンの出口であり、凝縮器の入口です。タービンによる膨張過程を考えます。

*   圧力: $P_4 = P_1$ (凝縮圧力)
*   理想的なタービン仕事 (等エントロピー過程):
    $s_{4s} = s_3$
    $h_{4s} = \text{PropsSI}("H", "P", P_4, "S", s_{4s} \times 1000, \text{fluid}) / 1000$
*   実際のタービン出口エンタルピー (タービン効率 $\eta_{turb}$ を考慮):
    $h_4 = h_3 - \eta_{turb} (h_3 - h_{4s})$
*   温度: $T_4 = \text{PropsSI}("T", "P", P_4, "H", h_4 \times 1000, \text{fluid})$
*   比エントロピー: $s_4 = \text{PropsSI}("S", "P", P_4, "H", h_4 \times 1000, \text{fluid}) / 1000$

各状態点 $i \in \{1, 2, 3, 4\}$ における比エクセルギー $\psi_i$ は、前述の式 (1.2) を用いて計算されます。

$\psi_i = (h_i - h_0) - T_0 (s_i - s_0)$

## 4. コンポーネント解析

各コンポーネントにおけるエネルギーバランスとエクセルギー解析を行います。作動流体の質量流量を $\dot{m}_{orc}$ とします。

### 4.1 ポンプ

*   **消費仕事率 $\dot{W}_p$**:
    $\dot{W}_p = \dot{m}_{orc} (h_2 - h_1)$
*   **可逆仕事率 $\dot{W}_{p,rev}$ (エクセルギー変化率)**:
    $\dot{W}_{p,rev} = \dot{m}_{orc} (\psi_2 - \psi_1)$
*   **エクセルギー破壊率 $\dot{E}_{dest,p}$**:
    $\dot{E}_{dest,p} = \dot{W}_p - \dot{W}_{p,rev}$
*   **ポンプのエクセルギー効率 $\eta_{ex,p}$**:
    $\eta_{ex,p} = \frac{\dot{W}_{p,rev}}{\dot{W}_p} = \frac{\psi_2 - \psi_1}{h_2 - h_1}$ (ただし $\dot{W}_p \neq 0$)

### 4.2 蒸発器

*   **受熱量 $\dot{Q}_e$**:
    $\dot{Q}_e = \dot{m}_{orc} (h_3 - h_2)$
*   **熱源からの熱エクセルギー供給率 $\dot{E}_{Q,e}$**:
    熱媒体の入口温度 $T_{htf,in}$ と出口温度 $T_{htf,out}$ が与えられている場合、熱源の平均温度 $T_{hot,avg}$ は $T_{hot,avg} = 0.5 (T_{htf,in} + T_{htf,out})$ として近似されます。
    $\dot{E}_{Q,e} = \left(1 - \frac{T_0}{T_{hot,avg}}\right) \dot{Q}_e$
    LMTDは、 $T_{htf,in}, T_{htf,out}, T_2, T_3$ を用いて式 (1.1) に従って計算されます。
    $T_{htf,in}$ と $T_{htf,out}$ が与えられていない場合、フォールバックとして $T_{hot,avg} = 0.5 (T_2 + T_3)$ が使用され、LMTDは $T_3 - T_2$ となります。
*   **作動流体のエクセルギー増加量 $\Delta\dot{E}_{orc,e}$**:
    $\Delta\dot{E}_{orc,e} = \dot{m}_{orc} (\psi_3 - \psi_2)$
*   **エクセルギー破壊率 $\dot{E}_{dest,e}$**:
    $\dot{E}_{dest,e} = \dot{E}_{Q,e} - \Delta\dot{E}_{orc,e}$
*   **蒸発器のエクセルギー効率 $\varepsilon_e$ (合理的な効率とも呼ばれる)**:
    $\varepsilon_e = \frac{\Delta\dot{E}_{orc,e}}{\dot{E}_{Q,e}} = \frac{\dot{m}_{orc}(\psi_3 - \psi_2)}{\dot{E}_{Q,e}}$ (ただし $\dot{E}_{Q,e} \neq 0$)

### 4.3 タービン

*   **発生仕事率 $\dot{W}_t$**:
    $\dot{W}_t = \dot{m}_{orc} (h_3 - h_4)$
*   **可逆仕事率 $\dot{W}_{t,rev}$ (エクセルギー変化率)**:
    $\dot{W}_{t,rev} = \dot{m}_{orc} (\psi_3 - \psi_4)$
*   **エクセルギー破壊率 $\dot{E}_{dest,t}$**:
    $\dot{E}_{dest,t} = \dot{W}_{t,rev} - \dot{W}_t$
*   **タービンのエクセルギー効率 $\eta_{ex,t}$**:
    $\eta_{ex,t} = \frac{\dot{W}_t}{\dot{W}_{t,rev}} = \frac{h_3 - h_4}{\psi_3 - \psi_4}$ (ただし $\dot{W}_{t,rev} \neq 0$)

### 4.4 凝縮器

*   **放熱量 $\dot{Q}_c$** (通常、負の値):
    $\dot{Q}_c = \dot{m}_{orc} (h_1 - h_4)$
*   **冷却媒体への熱エクセルギー排出率 $\dot{E}_{Q,c}$**:
    冷却媒体の平均温度 $T_{cold,avg}$ は $T_{cold,avg} = 0.5 (T_4 + T_1)$ として近似されます。
    $\dot{E}_{Q,c} = \left(1 - \frac{T_0}{T_{cold,avg}}\right) \dot{Q}_c$
*   **作動流体のエクセルギー減少量 $\Delta\dot{E}_{orc,c}$**:
    $\Delta\dot{E}_{orc,c} = \dot{m}_{orc} (\psi_4 - \psi_1)$
*   **エクセルギー破壊率 $\dot{E}_{dest,c}$**:
    $\dot{E}_{dest,c} = \Delta\dot{E}_{orc,c} + \dot{E}_{Q,c}$
    (注意: $\dot{Q}_c$ が負であるため、$\dot{E}_{Q,c}$ も通常負またはゼロです。エクセルギー破壊は常に正であるべきなので、この定義は $\dot{E}_{dest,c} = (\text{入るエクセルギー}) - (\text{出るエクセルギー})$ の原則に基づいています。ここでは、作動流体からエクセルギーが減少し ($\psi_4 > \psi_1$ の場合)、熱としてエクセルギーが排出されます。)

## 5. サイクル全体の性能評価指標 (KPI)

*   **正味仕事率 $\dot{W}_{net}$**:
    $\dot{W}_{net} = \dot{W}_t - \dot{W}_p$
*   **熱効率 $\eta_{th}$**:
    $\eta_{th} = \frac{\dot{W}_{net}}{\dot{Q}_e}$ (ただし $\dot{Q}_e \neq 0$)
*   **エクセルギー効率 $\varepsilon_{ex}$ (または第二法則効率)**:
    $\varepsilon_{ex} = \frac{\dot{W}_{net}}{\dot{E}_{Q,e}}$ (ただし $\dot{E}_{Q,e} \neq 0$)
    これは、供給された熱エクセルギーのうち、どれだけが有効な仕事として取り出されたかを示します。

## 6. 熱源条件からのORC性能計算 (`calculate_orc_performance_from_heat_source`)

この関数は、外部の単相熱源の条件 (入口温度 $T_{htf,in}$、体積流量 $\dot{V}_{htf}$ など) に基づいてORCの運転パラメータを決定し、上記の `calculate_orc_performance` 関数を呼び出してサイクル性能を評価します。

### 6.1 熱源からの有効熱量とORC運転条件の決定

1.  **熱媒体の物性値**:
    熱媒体の密度 $\rho_{htf}$ と定圧比熱 $C_{p,htf}$ を $T_{htf,in}$ と $P_{htf}$ (熱媒体圧力) で評価します。
    $\rho_{htf} = \text{PropsSI}("Dmass", "T", T\_{htf,in}, "P", P\_{htf}, \text{fluid\_htf})$
    $C_{p,htf} = \text{PropsSI}("Cpmass", "T", T\_{htf,in}, "P", P\_{htf}, \text{fluid\_htf}) \quad [\text{J/(kg*K)}]$
2.  **熱媒体の質量流量 $\dot{m}_{htf}$**:
    $\dot{m}_{htf} = \rho_{htf} \cdot \dot{V}_{htf}$
3.  **ORC蒸発器の飽和温度 $T_{sat,evap}$**:
    指定されたピンチポイント温度差 $\Delta T\_{pinch}$ (K) と過熱度 $\Delta T\_{superheat}$ (K) を用いて、
    $T_{sat,evap} = T_{htf,in} - \Delta T\_{pinch} - \Delta T\_{superheat}$
    もし $T_{sat,evap} \le T_{cond} + 1.0$ K ならば、サイクルは成立しないと判断されます。
4.  **ORC蒸発圧力 $P_{evap}$**:
    $P_{evap} = \text{PropsSI}("P", "T", T_{sat,evap}, "Q", 1, \text{fluid\_orc})$ (ORC作動流体の飽和蒸気圧力)
5.  **タービン入口温度 $T_{turb,in}$**:
    $T_{turb,in} = T_{sat,evap} + \Delta T_{superheat}$
6.  **熱媒体の出口温度 $T_{htf,out}$**:
    $T_{htf,out} = T_{sat,evap} + \Delta T_{pinch}$
7.  **熱源からの有効熱量 $\dot{Q}_{available}$ (kW)**:
    $\dot{Q}_{available} = \frac{\dot{m}_{htf} \cdot C_{p,htf} \cdot (T_{htf,in} - T_{htf,out})}{1000}$
    もし $\dot{Q}_{available} \le 0$ ならば、サイクルは成立しないと判断されます。

### 6.2 ORC作動流体の質量流量 $\dot{m}_{orc}$ の推定

ORCの蒸発器におけるエンタルピー上昇 $\Delta h_{evap}$ を概算し、$\dot{m}_{orc}$ を決定します。

1.  状態点1 ($h_1, s_1$) は $T_{cond}$ から計算 (上記 3.2 節と同様)。
2.  状態点2 ($h_2$) は $P_{evap}$ と $\eta_{pump}$ を用いて計算 (上記 3.3 節と同様)。
3.  状態点3 ($h_3$) は $T_{turb,in}$ と $P_{evap}$ を用いて計算 (上記 3.4 節と同様)。
4.  蒸発器での比エンタルピー上昇 $\Delta h_{evap}$:
    $\Delta h_{evap} = h_3 - h_2$
    もし $\Delta h_{evap} \le 0$ ならば、サイクルは成立しないと判断されます。
5.  ORC作動流体の質量流量 $\dot{m}_{orc}$:
    $\dot{m}_{orc} = \frac{\dot{Q}_{available}}{\Delta h_{evap}}$

### 6.3 サイクル計算の実行

上記で決定された $P_{evap}$, $T_{turb,in}$, $\dot{m}_{orc}$ およびその他の入力パラメータ ($T_{cond}$, $\eta_{pump}$, $\eta_{turb}$, 作動流体の種類など) を用いて、`calculate_orc_performance` 関数が呼び出され、詳細なサイクル性能が計算されます。
この際、$T_{htf,in}$ と $T_{htf,out}$ も `calculate_orc_performance` に渡され、蒸発器のLMTD計算などに使用されます。

最終的に、サイクルKPI、各コンポーネントのエクセルギー破壊などの情報がまとめられて出力されます。
