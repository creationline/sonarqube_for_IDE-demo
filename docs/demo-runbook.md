# デモ運用ガイド

このファイルは、実際にデモを演じる人・記事を書く人のための手順書です。
「SonarQube for IDE が何をするものなのか」を知りたいだけなら、
まず [README.md](../README.md) を読んでください。

---

## 仕込んである 5 つの問題

| # | 問題 | ルール | 段 | 場所 |
|---|---|---|:---:|---|
| 1 | API キーのハードコード | `python:S6418` | 1 | [user_manager.py:40](../user_manager.py#L40) |
| 2 | パスワードのハードコード | `python:S2068` | 1 | [user_manager.py:51](../user_manager.py#L51) |
| 3 | いつも成功してしまう assert（テストコード） | `python:S5905` | 1 | [test_user_manager.py:108](../test_user_manager.py#L108) |
| 4 | ZIP の無制限展開（Zip Bomb） | `python:S5042` | 2 | [user_manager.py:78](../user_manager.py#L78) |
| 5 | 制御構文のネストが深すぎる | `python:S134` | 2 | [user_manager.py:113](../user_manager.py#L113) |

**5 件すべてを計算しているのは、手元の VS Code です。**
段を上げて増えるのは「エンジンの能力」ではなく、「どのルールが ON になっているか」だけです。

### 1・2 —— 誰も反対しないので既定で ON

ソースコードに秘密情報を直書きするのは、どんなチームでも問題です。
だから既定のルールセット `Sonar way` に最初から入っています。

### 3 —— テストコードも、まったく同じように解析される

**「テストコードだから見逃される」ということはありません。**
[test_user_manager.py](../test_user_manager.py) を開くと、
拡張機能を入れただけの状態で 1 件出ます。

```
python:S5905  Fix this assertion on a tuple literal.  (108行目)
```

```python
assert (result["rank"] == "S", "管理者で高得点なら S になるはず")
```

#### 何が起きているのか（誤解しやすいところ）

「括弧を付けるとテストが実行されなくなる」と説明されることがありますが、**そうではありません。**
テストは実行されます。`assert` の行も実行されます。比較そのものも計算されます。
壊れているのは **何を検査しているか** のほうです。

`assert` は関数ではないので、括弧を付けても「引数を囲んだ」ことになりません。括弧は**タプルを作ります**。

```
assert (result["rank"] == "S", "管理者で高得点なら S になるはず")

  ① 括弧の中身は評価される
     → result["rank"] == "S" は計算され、True か False になる

  ② その結果を第 1 要素にしたタプルが組み立てられる
     → (False, "管理者で高得点なら S になるはず")

  ③ assert が真偽を見るのは、この「タプルそのもの」
     → 空でないタプルは常に真 → この assert は絶対に失敗しない
```

①で出た比較結果は、②で袋に詰められた時点で誰にも見られなくなります。
**計算はされているのに、捨てられている**わけです。

#### なぜ厄介なのか

スキップされたテストなら、レポートに `skipped` と出るので気づけます。これは違います。
**堂々と PASS します。緑になります。**

実際、期待値をわざと壊しても通ります。実演ではここを見せると効きます。

```bash
# user_manager.py の {"rank": "S"} を {"rank": "Z"} に書き換えてから
$ python3 -m unittest test_user_manager -v
test_admin_with_high_score_is_rank_s ... ok    ← 期待値を壊しても ok のまま
```

分類は **BUG／Blocker**（`Sonar way` に収録済み）。

> Python 自身も `SyntaxWarning: assertion is always true, perhaps remove parentheses?`
> を出しますが、テストは PASS のままなので CI のログに流れて終わります。
> 「動いているから気づかない」タイプの不具合です。
> SonarQube for IDE は、これを**書いているその場で**赤い波線にします。

#### どう直すか

```python
# (1) 括弧を 2 文字消す —— これで assert は本来の形に戻る
assert result["rank"] == "S", "管理者で高得点なら S になるはず"

# (2) unittest なら assertEqual に書き換える（より安全）
self.assertEqual(result["rank"], "S", "管理者で高得点なら S になるはず")
```

(2) はそもそも関数なので、括弧を付けても壊れません。
失敗したときに「S を期待したが Z だった」という差分も出ます。

そして **(3) 直したあと、一度わざと失敗させて確かめる。**
期待値を `"S"` から `"Z"` に変えて実行し、赤くなることを見ます。
落ちなければ、そのテストはまだ何も守っていません。

保存して再解析されると指摘が消え、
「**このテストコードは問題ありません**」の状態になります。
デモとしては「出す → その場で消す」まで一気に見せられる、いちばん軽い 1 件です。

> **Quick Fix は当てにしないでください。**
> このルールには「Remove parentheses」という Quick Fix が用意されていますが、
> 要素が 1 個のタプル `assert (x,)` のときだけ提供されます。
> 今回のような 2 要素の形では電球が出ないので、手で消します。

#### なぜ「テスト専用ルール」は 1 つも動いていないのか

ここは少し意外なところです。Python アナライザには
`unittest` / `pytest` 専用のルール（scope が `Tests`）が **39 個**入っていて、
うち **37 個は `Sonar way` で ON** です。
にもかかわらず、既定の状態では**そのどれも動きません。**

理由はルールの「適用範囲（scope）」です。

| scope | 意味 | テスト系ルールの数 |
|---|---|:---:|
| `All` | ファイルの種類を問わず適用される | **2 個**（`python:S5905` と `python:S8405`） |
| `Tests` | **テストファイルと判定されたファイルにだけ**適用される | 39 個 |

そして SonarQube for IDE は、**既定では「テストファイル」を 1 つも持っていません。**
判定材料が `sonarlint.testFilePattern` という設定しかなく、その既定値が空だからです
（Java だけは例外で、vscode-java のクラスパスから自動判定されます）。

【3】に選んだ `python:S5905` は scope が `All` なので、
テスト判定に一切依存せず、入れるだけで出ます。

#### バインドすると挙動は変わるのか

**既定のままなら変わりません。** ただし、判定の仕組みは切り替わっています。

| | 未連携（第 1 段） | バインド後（第 2 段） |
|---|---|---|
| テストファイルの判定材料 | `sonarlint.testFilePattern` | サーバー側の `sonar.tests` / `sonar.test.inclusions` |
| その既定値 | 空 → 何もテストではない | 空 → 何もテストではない |
| scope `Tests` の 37 ルール | 動かない | **サーバー側で宣言しなければ、やはり動かない** |
| 【3】（scope `All`） | 出る | 出る（**変化なし**） |

つまり、テストコードの解析も**第 1 段と第 2 段を分ける線とまったく同じ構図**です。
テスト専用の 37 ルールを働かせたいなら、各自が

```jsonc
"sonarlint.testFilePattern": "**/test_*.py,**/*_test.py"
```

と書くか、サーバー側でテストソースを宣言するしかありません。
どちらも「誰かが設定する」という運用の話で、技術的な壁ではありません。

> **デモでの注意：** テスト専用ルールを有効にすると件数が変わります。
> 3 件 → 5 件の before / after を撮るときは、この設定を**空のまま**にしてください。

### 4・5 —— 「チームの判断」が要るので既定は OFF

Python のアナライザには 435 個のルールが同梱されていますが、
既定で有効なのは 398 個。**残りの 37 個は最初から OFF** です。

- **4（Zip Bomb）**: `extractall()` は展開後のサイズを確認せずに全部書き出します。
  数十 KB の ZIP が数十 GB に膨らむ細工が可能で、ディスクを埋め尽くされます。
  ただし、社内の信頼できるファイルしか扱わないなら過剰、という判断もありえます。
- **5（深いネスト）**: 何段まで許すかはチームの好み次第です。
  このルールの既定の上限は 4 段で、デモのコードは 5 段になっています。

OFF なのは「間違ったルール」だからではなく、**有効にするかがチームの判断だから**です。
逆に言えば、チームで決めた基準を全員の IDE に配るには連携が要る、ということです。

**判定するルール自体は、最初から手元にあります。**
だからバインドした瞬間に、push もサーバーの待ち時間もなしで 2 件増えます。

---

## はじめて SonarQube for IDE を使う人へ

「連携する」と一言で言っていますが、実際には**性質の違う 3 つの作業**があります。
ここを分けて理解しておくと、あとの手順で迷いません。

```
  A. インストール      拡張機能を入れる
        ↓                          ← ここまでで第 1 段（3 件）が動く
  B. 接続（Connection）  「どのサーバーの、誰として」を登録する
        ↓                            … VS Code 全体に 1 回だけ
  C. バインド（Binding） 「このフォルダは、どのプロジェクトか」を紐づける
                                     … フォルダごとに 1 回ずつ
        ↓                          ← ここで第 2 段（5 件）になる
  D. 共有              C の情報をリポジトリにコミットして、チームに配る
```

**B と C は別物です。** ここが最大のつまずきポイントで、
「接続したのに指摘が増えない」の原因はほぼ 100% これです。

ルールが同期される単位は接続ではなく**バインドされたプロジェクト**なので、
B だけでは 1 つも降りてきません。

| | 単位 | 何を決めるか |
|---|---|---|
| **B. 接続** | VS Code 全体 | サーバーの URL と、あなたが誰か（トークン） |
| **C. バインド** | フォルダごと | このフォルダがサーバー上のどのプロジェクトか |

1 つの接続に対して、バインドは複数ぶら下がります。

```
接続「社内 SonarQube」
  ├─ ~/work/web-app     ↔  project-web
  ├─ ~/work/api-server  ↔  project-api
  └─ ~/work/batch       ↔  project-batch
```

### 公式ドキュメント

- [Setting up connected mode](https://docs.sonarsource.com/sonarqube-for-vs-code/connect-your-ide/setup) — 上記 B・C・D の全体
- [First-time connection setup for shared binding](https://docs.sonarsource.com/sonarqube-for-vs-code/connect-your-ide/setup#first-time-connection-setup-for-shared-binding) — チームで最初のひとりがやる作業（D まで）
- [Bind using shared configuration](https://docs.sonarsource.com/sonarqube-for-vs-code/connect-your-ide/setup#bind-using-shared-configuration) — 2 人目以降がやる作業（通知に答えるだけ）

このリポジトリは **2 人目以降の体験**を再現できるようにしてあります。
`.sonarlint/connectedMode.json` をコミットしておけば、
B と C が 1 つの流れにまとまり、「プロジェクトを探して選ぶ」工程が消えます。

---

## 事前準備

VS Code の拡張機能マーケットプレイスで **SonarQube for IDE**（発行元 SonarSource）を
インストールする。**以上です。**

`user_manager.py` と `test_user_manager.py` は Python の標準ライブラリだけで書いてあります。
`pip install` するものは何もなく、仮想環境も要りません。
テストも `unittest` なので、pytest すら不要です。
クローンしてファイルを開けば、その場で解析が始まります。

依存がゼロなのは意図的です。外部パッケージを import すると Pylance の
「インポートを解決できませんでした」が Problems タブに混ざり、
「SonarQube の指摘は何件か」がひと目で分からなくなります。
そのおかげで Problems タブには **SonarQube の指摘しか出ません**。

動かして確かめたい場合は、そのまま実行できます。

```bash
python3 user_manager.py
# → {'rank': 'S'}

python3 -m unittest test_user_manager -v
# → 2 tests, OK（【3】があっても PASS してしまうことの確認）
```

---

## デモの手順

### 第 1 段：入れるだけ（3 件）

#### user_manager.py —— 2 件

1. VS Code でこのリポジトリを開く
2. [user_manager.py](../user_manager.py) を開く
3. **Problems**（問題）タブを開く

→ SonarQube の指摘が **2 件** 表示されます。

```
python:S6418  "API_KEY" detected here, make sure this is not a hard-coded secret.       (40行目)
python:S2068  "password" detected here, review this potentially hard-coded credential.  (51行目)
```

波線にカーソルを合わせて **Show rule description** を開くと、
「なぜ危険か」「どう直すか」の解説がサイドパネルに出ます。
ここまで、アカウント登録もサーバーも要りません。

そのうえで、**78・113 行目には何も波線が出ていない**ことを確認してください。
ここが記事の山場になります。

#### test_user_manager.py —— さらに 1 件（合計 3 件）

4. [test_user_manager.py](../test_user_manager.py) を開く

→ 108 行目に 1 件出ます。**テストコードも同じ扱いで解析されている**ことの確認です。

```
python:S5905  Fix this assertion on a tuple literal.  (108行目)
```

分類は **BUG／Blocker**。`assert` に括弧を付けたせいでタプルを渡しており、
このテストは**何が起きても PASS します**
（[詳細](#3--テストコードもまったく同じように解析される)）。

**そして、その場で直せます。**

5. 108 行目の括弧を 2 文字削って `assert result["rank"] == "S", "…"` にする
6. 保存する → **指摘が消える**

「このテストコードは問題ありません」という状態を、その場で作れる 1 件です。
指摘を出して、直して、消える —— ここまでを 30 秒で見せられます。

> **撮り終わったら Ctrl+Z で戻してください。**
> 直したままだと、このあとの第 2 段が 5 件ではなく 4 件になります。

### 第 2 段：サーバーに繋いでバインドする（5 件）

#### ステップ 1 — サーバー側で品質プロファイルを作る

1. SonarQube のサーバーにこのリポジトリのプロジェクトを作る
2. **Quality Profiles** で `Sonar way (Python)` を **Copy** し、`Team way` などの名前で複製する
3. 複製したプロファイルに、次の 2 つのルールを **Activate** で追加する
   - `python:S5042` — Expanding archive files should not be done without controlling resource consumption
   - `python:S134` — Control flow statements should not be nested too deeply
4. プロジェクトの **Administration → Quality Profiles** で、Python に `Team way` を割り当てる

#### ステップ 2 — IDE をバインドする

リポジトリのルートに `.sonarlint/connectedMode.json` を置き、
**中の 2 行を自分の環境に書き換えてください。**

```json
{
    "sonarCloudOrganization": "ここを自分の組織キーに",
    "projectKey": "ここをステップ 1 で作ったプロジェクトのキーに",
    "region": "EU"
}
```

SonarQube Server（オンプレ）を使っている場合は、代わりにこの形式です。

```json
{
    "sonarQubeUri": "https://sonarqube.example.com",
    "projectKey": "ここをステップ 1 で作ったプロジェクトのキーに"
}
```

書き換えてフォルダを開き直すと、**バインドを促す通知が出ます**。

5. 通知の **`Use Configuration`** を押す
6. 接続設定画面が開く。組織キーとプロジェクトキーは**入力済み**なので、
   **`Generate Token`** を押してトークンを発行する
7. **`Save Connection And Bind Project`** を押す（接続の作成とバインドが同時に完了する）
8. [user_manager.py](../user_manager.py) を開き直す

→ `user_manager.py` の指摘が **4 件** に増えます。

```
python:S6418  (40行目)
python:S2068  (51行目)
python:S5042  Make sure that expanding this archive file is safe here.                 (78行目)
python:S134   Refactor this code to not nest more than 4 "if", "for", ... statements.  (113行目)
```

`test_user_manager.py` の【3】は**バインド前と変わらず 1 件のまま**です
（`python:S5905` は scope が `All` なので、テスト判定にも品質プロファイルの
差分にも影響されません）。合わせて **5 件**になります。

**コードを push する必要はありません。**
解析そのものは手元の IDE で走っており、サーバーから受け取っているのは
「どのルールを有効にするか」という設定だけだからです。
バインドした直後、その場で 2 件増えます。

#### 逆向きにも効きます

サーバー側で誰かが「この指摘は対応しない」と決めた項目は、
各自のエディタからも消えます。**チーム全員が同じ判断結果を見る**——
これが Connected Mode の実務上の価値です。

---

## チーム全員に配る仕組み

第 2 段の手順で「プロジェクトを探して選ぶ」工程が無かったのは、
`.sonarlint/connectedMode.json` がリポジトリにコミットされているからです。

**サーバーは IDE に何かを送りつけることはできません。** 通信は常に IDE 側から取りに行く向きで、
サーバーは誰がいつリポジトリをクローンしたかを知りませんし、その端末に到達する経路も持ちません。
つまり「このフォルダはどのプロジェクトなのか」という手がかりは、
**リポジトリの中にファイルとして入っている以外に、開発者の手元へ届く方法がありません。**

このファイルは自分で書く必要はなく、一度バインドしたあとにコマンドパレットから

```
SonarQube: Share Connected Mode Configuration
```

を実行すると生成されます。あとはコミットするだけです。

同じ働きをするファイルは他にもあり、拡張機能は次の 3 つを手がかりとして読みます。

| ファイル | 読まれるキー |
|---|---|
| `.sonarlint/connectedMode.json` | `projectKey` / `sonarCloudOrganization` / `sonarQubeUri` / `region` |
| `sonar-project.properties` | `sonar.projectKey` / `sonar.organization` / `sonar.host.url` |
| `.sonarcloud.properties` | 同上 |

CI で解析を回しているチームなら `sonar-project.properties` が既にあるはずなので、
**何もしなくても自動バインドの提案が出ます。**

### ただし、トークンだけは各自が用意します

共有ファイルに入るのは**プロジェクトの識別情報だけ**です。
トークンをリポジトリに置くと、リポジトリを読める全員がそのユーザーとして
サーバーを操作できてしまうため、意図的に分離されています。

| | 共有される | 各自が用意 |
|---|---|---|
| 組織キー・プロジェクトキー | ✅ | |
| 接続先 URL / リージョン | ✅ | |
| **トークン** | | ✅ |

拡張機能の設定説明にも
*"For security reasons, the token should not be stored in SCM with workspace settings."*
と明記されています。**完全なゼロ設定にはならず、それは欠陥ではなく設計です。**

なお、発行するのは**ユーザートークン**である必要があります。
プロジェクトトークン／グローバルトークン／スコープ付き組織トークンでは正しく動作しません。

### トークンは 1 つだけ

よくある誤解ですが、「プロファイルを取ってくるトークン」と
「どのプロファイルを使うか決めるトークン」が別々にある、ということはありません。

| | 何を決めるか | どこにある |
|---|---|---|
| **トークン** | **あなたが誰か**（認証） | 各自の VS Code |
| **`projectKey`** | **どのプロジェクトの設定が欲しいか** | `.sonarlint/connectedMode.json` |
| **プロファイルの割り当て** | **そのプロジェクトに何を適用するか** | **サーバー側の設定** |

IDE が実際に叩いているのは、認証つきのこの 1 本だけです。

```
GET /api/qualityprofiles/search.protobuf?project=<projectKey>&organization=<org>
```

「私は〇〇です。プロジェクト X の設定をください」と言っているだけで、
X に何を適用するかはサーバーが決めています。
だから**サーバー側で 1 回変えれば、バインドしている全員に行き渡ります。**

---

## スクリーンショットの撮りどころ

| # | 撮る場面 | 記事での役割 |
|---|---|---|
| 1 | 第 1 段の `user_manager.py`（2 件） | 「入れただけでこれだけ出る」 |
| 2 | 波線ホバー → Show rule description | 「解説まで読める」 |
| 3 | 78・113 行目に波線が無い状態 | 「でも、これは見逃す」 |
| 4 | 第 1 段の `test_user_manager.py`（108 行目に 1 件） | 「テストコードも同じように見ている」 |
| 5 | **4 の括弧を消した直後（指摘が消えた状態）** | **「直せば、その場で消える」** |
| 6 | 期待値を壊しても `ok` になるテスト実行ログ | **「PASS しているのに何も守っていない」** |
| 7 | サーバー側の品質プロファイル編集画面 | 「チームの基準を決める場所」 |
| 8 | 「Use Configuration」のバインド提案通知 | 「クローンしただけで声がかかる」 |
| 9 | 第 2 段の `user_manager.py`（4 件） | 「繋ぐと 2 件増える」 |

**1 と 9 を並べた before / after が一番伝わります。**
そこに 3 を挟むと「なぜ増えたのか」の導線になります。

4・5・6 は、このデモで一番反応があるパートです。
4 と 5 を横に並べると「検知 → 修正 → 解決」が 1 枚で伝わり、
6 を足すと「テストが通っていること自体は嘘ではない」という肝が伝わります。
**5 を撮ったら Ctrl+Z で戻してください。** 直したままだと 9 のあとの合計が 5 件になりません。

**8 を撮るときの注意：** 一度バインドすると `.vscode/settings.json` が優先され、
通知は二度と出ません。**別のディレクトリにクローンし直してください。**
パスが変われば別ワークスペース扱いになり、初回状態の通知が出ます。

---

## つまずきやすいポイント

- **「接続」と「バインド」は別物です。**
  接続を登録しただけではフォルダは紐づきません。ルールが同期されるのは
  **バインドされたプロジェクト単位**なので、接続だけでは 1 つも降ってきません。
  バインドできていると `.vscode/settings.json` に
  `sonarlint.connectedMode.project` が実際の値入りで書き込まれます。
- **`.vscode/settings.json` に空の設定が残っていると、通知が出ません。**
  設定 UI から `sonarlint.connectedMode.project` を開くと、VS Code が
  `{"connectionId": "", "projectKey": ""}` という空の雛形を書き込むことがあります。
  この状態はバインド済みではないのに「設定済み」と見なされ、提案が抑制されます。
  中身が空文字だったら、ファイルごと削除してください。
- **通知で `Don't Ask Again` を押さないでください。**
  `doNotAskAboutConnectionSetupForWorkspace` にワークスペース単位で永続化され、
  そのフォルダでは二度と通知が出ません。リハーサル中に押すとデモが撮れなくなります。
- **品質プロファイルを割り当て忘れると 3 件のままです。**
  複製しただけでは効きません。プロジェクトに割り当てるところまでやってください。
- **`sonarlint.focusOnNewCode` が有効だと件数が減って見えます。**
  「新しいコードだけ」に絞る設定です。デモ中は無効にしておくと安定します。
- **`pip install` はしないでください。**
  依存ゼロなのは意図的です。実際に import すると Pylance の
  「インポートを解決できませんでした」が Problems タブに混ざり、
  「SonarQube の指摘は何件か」がひと目で分からなくなります。
  VS Code が「仮想環境を作りますか」と聞いてきたら、断って構いません。
- **【5】の `user_rank()` に条件を足さないでください。**
  現在の認知的複雑度は 15 で、`python:S3776`（既定 ON、閾値 15 超で発報）の
  ぎりぎり手前です。1 つ足すと第 1 段で 1 件増えてしまい、デモが崩れます。
- **【4】は `with zipfile.ZipFile(...) as f:` の形にしないでください。**
  その書き方だと型解決が効かず、ルールを有効にしても検知されません。
  `zipfile.ZipFile(...).extractall(...)` の直接呼び出しにしてあります。
- **`sonarlint.testFilePattern` は空のままにしてください。**
  ここに `**/test_*.py` などを書くと、`test_user_manager.py` がテストファイルと
  判定され、scope が `Tests` の 37 ルールが一斉に効きはじめます。
  【3】自体は scope `All` なので消えませんが、**件数が変わってデモが崩れます。**
- **`test_user_manager.py` にテストを足すときは注意してください。**
  似たテストを 3 つ以上並べると `python:S5976`（Parameterized にまとめよ）、
  `assertTrue(a == b)` と書くと `python:S5906`（もっと具体的な assert を使え）
  —— どちらも scope `Tests` なので**既定では出ませんが**、
  テストファイル判定を有効にした環境では出ます。
- **【3】の Quick Fix を待たないでください。**
  「Remove parentheses」は 1 要素タプルのときだけ提供されます。
  今回の 2 要素の形では電球が出ないので、手で括弧を消します。

---

## 補足：段の間の線は、設定でも越えられます

4・5 のルールは拡張機能に同梱されているので、
VS Code のユーザー設定に次を書けば、サーバーに繋がなくても有効にできます。

```jsonc
"sonarlint.rules": {
  "python:S5042": { "level": "on" },
  "python:S134":  { "level": "on" }
}
```

テストコード用のルールも同じです。テストファイル判定を自分で書けば、
scope が `Tests` の 37 ルールも連携なしで動きはじめます。

```jsonc
"sonarlint.testFilePattern": "**/test_*.py,**/*_test.py"
```

つまり第 1 段と第 2 段を分けているのは、**技術ではなく運用**です。
伝えたいのは

> 開発者ひとりひとりが手元で設定しない限り、チームの基準は誰の IDE にも効かない。

ということで、繋げばその設定作業がゼロになる、という話です。

| | 第 1 段（3 件） | 第 2 段（5 件） |
|---|---|---|
| 解析する場所 | 手元の PC | 手元の PC（**同じ**） |
| 見ている範囲 | 開いているファイル | 開いているファイル（**同じ**） |
| 使うルール表 | 拡張機能に同梱の `Sonar way` | サーバーから下りてきた品質プロファイル |
| 行き来するもの | なし | **ルール設定だけ**（コードは出ない） |
| push は要るか | 不要 | **不要** |
| 結果が出るまで | 入力しながら即時 | 入力しながら即時（**同じ**） |
| 各自の設定で代替できるか | ― | **できる**（上記 `sonarlint.rules`） |

**繋ぐことの価値は「見える件数」ではなく、「全員が同じ基準で見る」ことのほうです。**

---

## ファイル構成

```
.
├── README.md                       機能の紹介（まずここ）
├── user_manager.py                 デモ対象。【1】【2】【4】【5】を仕込んである
├── test_user_manager.py            テストコード。【3】を仕込んである（unittest）
├── .sonarlint/
│   └── connectedMode.json          バインド先の共有設定（各自の組織キーに要書き換え）
└── docs/
    ├── analysis-reach.html         縦スクロールの図解
    ├── demo-story.md               記事の導入に置く見取り図
    ├── demo-runbook.md             このファイル
    └── figures/                    図版（SVG と PNG）
```
