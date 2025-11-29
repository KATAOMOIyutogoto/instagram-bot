"""
Google Business Profile の account_id と location_id を取得するスクリプト

使用方法:
1. config/credentials.json と config/token.json を準備
2. python scripts/get_gbp_ids.py を実行
3. 表示された account_id と location_id を config/config.json に設定
"""

import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from src.google_business_api import GoogleBusinessProfileAPI
except ImportError:
    print("エラー: google_business_api モジュールが見つかりません")
    print("必要なライブラリをインストールしてください:")
    print("pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)


def get_accounts_and_locations(
    credentials_path="config/credentials.json", token_path="config/token.json", retry_count=3
):
    """
    Google Business Profile のアカウントとロケーション一覧を取得

    Args:
        credentials_path: 認証情報ファイルのパス
        token_path: トークンファイルのパス
        retry_count: リトライ回数（デフォルト: 3回）

    Returns:
        アカウントとロケーションの情報
    """
    api = None
    last_error = None

    # APIクライアントの初期化をリトライ
    for attempt in range(retry_count):
        try:
            print(f"Google Business Profile API に接続中... (試行 {attempt + 1}/{retry_count})")
            api = GoogleBusinessProfileAPI(credentials_path=credentials_path, token_path=token_path)
            print("接続成功！")
            break  # 成功したらループを抜ける
        except Exception as e:
            last_error = e
            if attempt < retry_count - 1:
                print(f"接続に失敗しました: {e}")
                print(f"再試行します... ({attempt + 1}/{retry_count})")
                import time

                time.sleep(2)  # 2秒待機してから再試行
            else:
                print(f"接続に失敗しました（{retry_count}回試行）: {e}")
                raise

    if api is None:
        raise Exception("APIクライアントの初期化に失敗しました")

    try:

        # アカウント一覧を取得
        print("\nアカウント一覧を取得中...")
        try:
            accounts_response = api.service.accounts().list().execute()
            accounts = accounts_response.get("accounts", [])
        except Exception as e:
            # mybusiness v4 APIの場合、エンドポイントが異なる可能性がある
            print(f"アカウント一覧の取得に失敗しました: {e}")
            print("\n代替方法: 直接ロケーションを取得します...")
            # 直接ロケーションを取得する方法を試す
            # 注意: この場合、account_id を手動で指定する必要があるかもしれません
            return None

        if not accounts:
            print("⚠️  アカウントが見つかりませんでした")
            print(
                "Google Business Profile Manager でアカウントが正しく設定されているか確認してください"
            )
            return None

        print(f"\n✅ {len(accounts)}個のアカウントが見つかりました\n")

        all_locations = []

        # 各アカウントのロケーションを取得
        for account in accounts:
            account_name = account.get("name", "")
            account_id = account_name.split("/")[-1] if "/" in account_name else account_name
            account_name_display = account.get("accountName", account_id)

            print(f"📋 アカウント: {account_name_display}")
            print(f"   account_id: {account_id}")
            print("   ロケーション一覧を取得中...")

            try:
                # ロケーション一覧を取得
                locations_response = (
                    api.service.accounts().locations().list(parent=account_name).execute()
                )
                locations = locations_response.get("locations", [])

                if locations:
                    print(f"   ✅ {len(locations)}個のロケーションが見つかりました:\n")
                    for location in locations:
                        location_name = location.get("name", "")
                        location_id = (
                            location_name.split("/")[-1] if "/" in location_name else location_name
                        )

                        # 店舗名を取得
                        store_name = location.get("storefrontAddress", {}).get("addressLines", [""])
                        store_name = store_name[0] if store_name else location.get("title", "N/A")

                        print(f"   📍 {store_name}")
                        print(f"      location_id: {location_id}")
                        print()

                        all_locations.append(
                            {
                                "account_id": account_id,
                                "account_name": account_name_display,
                                "location_id": location_id,
                                "store_name": store_name,
                            }
                        )
                else:
                    print("   ⚠️  ロケーションが見つかりませんでした\n")

            except Exception as e:
                print(f"   ❌ ロケーション取得エラー: {e}\n")
                continue

        return all_locations

    except FileNotFoundError as e:
        print(f"[ERROR] 認証情報ファイルが見つかりません: {e}")
        print("\n以下のファイルを準備してください:")
        print(f"  - {credentials_path}")
        if not Path(credentials_path).exists():
            print("    → Google Cloud Console から認証情報をダウンロードしてください")
        print(f"  - {token_path}")
        print("    → 初回実行時に自動生成されます")
        return None
    except ValueError as e:
        error_msg = str(e)
        if "認証コード" in error_msg or "認証" in error_msg:
            print(f"[ERROR] 認証エラー: {e}")
            print("\n解決方法:")
            print("1. 認証コードを正しくコピー＆ペーストしてください")
            print("2. 認証コードの前後に空白が含まれていないか確認してください")
            print("3. 認証コードの有効期限（通常10分）が切れていないか確認してください")
            print("4. 再度実行して、新しい認証コードを取得してください")
        else:
            print(f"[ERROR] エラー: {e}")
        return None
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] エラー: {e}")

        # エラーの種類に応じた詳細なメッセージ
        if "redirect_uri" in error_msg.lower():
            print("\nリダイレクトURIエラーが発生しました。")
            print("解決方法:")
            print("1. Google Cloud Console で以下のリダイレクトURIが設定されているか確認:")
            print("   - urn:ietf:wg:oauth:2.0:oob")
            print("   - http://localhost")
            print("   - http://localhost:8080")
            print("2. python scripts/setup_credentials.py を実行して credentials.json を確認")
        elif "credentials" in error_msg.lower() or "認証情報" in error_msg:
            print("\n認証情報エラーが発生しました。")
            print("解決方法:")
            print("1. config/credentials.json が正しい形式か確認")
            print("2. python scripts/setup_credentials.py を実行して設定を確認")
        elif "token" in error_msg.lower() or "トークン" in error_msg:
            print("\nトークンエラーが発生しました。")
            print("解決方法:")
            print("1. config/token.json を削除して再認証")
            print("2. 再度実行して新しいトークンを取得")
        else:
            import traceback

            print("\n詳細なエラー情報:")
            traceback.print_exc()

        return None


def generate_config_example(locations):
    """
    config.json用の設定例を生成

    Args:
        locations: ロケーション情報のリスト
    """
    if not locations:
        return

    print("=" * 60)
    print("📝 config.json の設定例")
    print("=" * 60)
    print()
    print("以下の設定を config.json の targets.companies に追加してください:\n")

    # Instagram IDごとにグループ化（ここでは例として1つのInstagram IDに1つのロケーションを紐づけ）
    print("【設定例】")
    print()

    for idx, loc in enumerate(locations, 1):
        print(f"例{idx}: {loc['store_name']} の場合")
        print("```json")
        print("{")
        print('  "instagram_id": "あなたのInstagramID",')
        print('  "google_business_locations": [')
        print("    {")
        print(f'      "account_id": "{loc["account_id"]}",')
        print(f'      "location_id": "{loc["location_id"]}"')
        print("    }")
        print("  ]")
        print("}")
        print("```")
        print()

    # 複数ロケーションの例
    if len(locations) > 1:
        print("【複数ロケーションの例】")
        print("1つのInstagramアカウントに複数のロケーションを紐付ける場合:")
        print("```json")
        print("{")
        print('  "instagram_id": "あなたのInstagramID",')
        print('  "google_business_locations": [')
        for loc in locations:
            print("    {")
            print(f'      "account_id": "{loc["account_id"]}",')
            print(f'      "location_id": "{loc["location_id"]}"')
            print("    },")
        print("  ]")
        print("}")
        print("```")
        print()


def main():
    """メイン関数"""
    print("=" * 60)
    print("Google Business Profile ID 取得ツール")
    print("=" * 60)
    print()

    # 認証情報ファイルの確認
    credentials_path = "config/credentials.json"
    token_path = "config/token.json"

    if not Path(credentials_path).exists():
        print(f"❌ {credentials_path} が見つかりません")
        print("Google Cloud Console から認証情報をダウンロードしてください")
        return

    if not Path(token_path).exists():
        print(f"[INFO] {token_path} が見つかりません")
        print("初回実行時に自動生成されます。")
        print("認証が必要な場合、ブラウザで認証URLが開きます。")
        print()

    # アカウントとロケーションを取得
    locations = get_accounts_and_locations(credentials_path, token_path)

    if locations:
        print("=" * 60)
        print("✅ 取得完了")
        print("=" * 60)
        print()

        # config.json用の設定例を生成
        generate_config_example(locations)

        # JSON形式でも出力
        print("=" * 60)
        print("📋 JSON形式の出力")
        print("=" * 60)
        print(json.dumps(locations, indent=2, ensure_ascii=False))
        print()

    else:
        print("\n⚠️  ロケーション情報を取得できませんでした")
        print("\n確認事項:")
        print("1. credentials.json と token.json が正しく設定されているか")
        print("2. Google Business Profile API が有効になっているか")
        print("3. アカウントにロケーションが登録されているか")
        print("4. 認証に使用しているGoogleアカウントに適切な権限があるか")


if __name__ == "__main__":
    main()
