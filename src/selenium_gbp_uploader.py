"""
SeleniumベースのGoogle Business Profileアップローダー
postGBP.py の機能をクラス化して統合
"""

import base64
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    from webdriver_manager.chrome import ChromeDriverManager
    import undetected_chromedriver as uc

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logging.warning(
        "Seleniumライブラリがインストールされていません。pip install selenium webdriver-manager undetected-chromedriver を実行してください。"
    )

logger = logging.getLogger(__name__)


class SeleniumGBPUploader:
    """SeleniumベースのGoogle Business Profileアップローダー"""

    def __init__(
        self,
        chrome_profile_path: str | None = None,
        profile_name_gbp: str | None = None,
        logger_instance: logging.Logger | None = None,
    ):
        """
        Args:
            chrome_profile_path: Chromeプロファイルのパス
            profile_name_gbp: GBP用のプロファイル名
            logger_instance: ロガーインスタンス（Noneの場合は共通ロガーを使用）
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError(
                "Seleniumライブラリがインストールされていません。\n"
                "以下のコマンドでインストールしてください：\n"
                "pip install selenium webdriver-manager undetected-chromedriver"
            )

        self.chrome_profile_path = chrome_profile_path
        self.profile_name_gbp = profile_name_gbp
        self.logger = logger_instance or logger
        self.driver = None

    def _get_chrome_driver(self):
        """Chromeドライバーを取得"""
        try:
            # 既存のChromeプロセスを終了（Windows用）
            if os.name == "nt":
                subprocess.run("taskkill /F /IM chrome.exe", shell=True, stderr=subprocess.DEVNULL)

            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")

            # Chromeプロファイルの設定
            if self.chrome_profile_path:
                chrome_options.add_argument(f"--user-data-dir={self.chrome_profile_path}")
            if self.profile_name_gbp:
                chrome_options.add_argument(f"--profile-directory={self.profile_name_gbp}")

            # その他の必要なオプション
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_experimental_option("detach", False)
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--no-service-autorun")
            chrome_options.add_argument("--password-store=basic")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")

            # プリファレンス設定
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.media_stream_mic": 2,
                "profile.default_content_setting_values.media_stream_camera": 2,
            }
            chrome_options.add_experimental_option("prefs", prefs)
            chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            return self.driver

        except Exception as e:
            self.logger.error(f"Chromeドライバーの設定でエラーが発生しました: {e}")
            self.logger.error("注意: Chromeを完全に終了してから実行してください")
            return None

    def _encode_google_business_param(self, location_id: str) -> str:
        """Google Business Profile のパラメータをエンコード"""
        param_list = [None, None, None, 1, None, None, location_id]
        json_str = json.dumps(param_list)
        encoded = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
        # base64のパディング(=)をピリオド(.)に置換
        return encoded.rstrip("=") + "."

    def _create_business_post(self, location_id: str):
        """対象のGBPの投稿画面に遷移"""
        encoded_param = self._encode_google_business_param(location_id)
        url = f"https://business.google.com/locations/search?hl=ja&lq={encoded_param}"
        self.logger.info(f"エンコードURL: {url}")

        if not self.driver:
            self.driver = self._get_chrome_driver()
            if not self.driver:
                self.logger.error("Chromeドライバーの取得に失敗しました")
                return None

        self.driver.get("https://www.google.com/")
        time.sleep(3)
        self.driver.get(url)
        time.sleep(5)

        try:
            wait = WebDriverWait(self.driver, 10)
            post_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[jsname="nFHyHb"]')))
            post_button.click()
            time.sleep(3)
            return self.driver
        except Exception as e:
            self.logger.error(f"投稿画面への遷移エラー: {e}")
            if self.driver:
                self.driver.quit()
            return None

    def _switch_to_post_frame(self, driver):
        """iframeに切り替え"""
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
            time.sleep(3)

            frames = driver.find_elements(By.TAG_NAME, "iframe")
            self.logger.info(f"Found {len(frames)} frames")

            for frame in frames:
                try:
                    driver.switch_to.frame(frame)
                    file_input = driver.find_element(By.CSS_SELECTOR, 'input.u5Dfnd[type="file"]')
                    self.logger.info("Found correct frame")
                    return True
                except:
                    driver.switch_to.default_content()
                    continue

            self.logger.warning("Could not find the correct frame")
            return False
        except Exception as e:
            self.logger.error(f"Error switching frames: {e}")
            return False

    def _upload_media_files(self, driver, file_paths: list[str], logger_instance: logging.Logger | None = None):
        """メディアファイルをアップロード"""
        log = logger_instance or self.logger

        try:
            if not self._switch_to_post_frame(driver):
                log.error("iframe切り替え失敗")
                return False, None

            # 動画変換機能と画像最適化機能をインポート
            from .utils import ensure_video_resolution, optimize_image_size

            last_file_path = None

            for file_path in file_paths:
                try:
                    file_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
                    )

                    abs_file_path = os.path.abspath(file_path)

                    # 動画の場合は解像度チェックと変換
                    if abs_file_path.lower().endswith((".mp4", ".mov", ".avi", ".wmv", ".webm", ".mkv")):
                        # 動画変換を実行
                        converted_path = ensure_video_resolution(abs_file_path)
                        abs_file_path = converted_path
                    # 画像の場合はサイズ最適化
                    elif abs_file_path.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                        # 画像最適化を実行
                        optimized_path = optimize_image_size(abs_file_path)
                        abs_file_path = optimized_path

                    log.info(f"アップロード中のファイル: {abs_file_path}")

                    file_input.send_keys(abs_file_path)

                    # ファイルタイプに応じて待機時間を調整
                    if abs_file_path.lower().endswith((".mp4", ".mov", ".avi", ".wmv")):
                        log.info("動画のアップロードを待機中...")
                        wait_time = 10
                    else:
                        log.info("画像のアップロードを待機中...")
                        wait_time = 3

                    time.sleep(wait_time)
                    last_file_path = abs_file_path

                except Exception as e:
                    log.error(f"{file_path} のアップロード中にエラーが発生しました: {str(e)}")

            return True, last_file_path

        except Exception as e:
            log.error(f"アップロード処理中にエラーが発生しました: {str(e)}")
            return False, None

    def _extract_caption_from_metadata(self, metadata_path: str) -> str | None:
        """メタデータファイルからキャプションを抽出"""
        try:
            if not Path(metadata_path).exists():
                self.logger.warning(f"メタデータファイルが見つかりません: {metadata_path}")
                return None

            with open(metadata_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            in_caption = False
            caption_lines = []

            for line in lines:
                if "--- キャプション ---" in line:
                    in_caption = True
                    continue
                if in_caption:
                    if line.startswith("---") and "キャプション" not in line:
                        break
                    else:
                        caption_lines.append(line)

            if caption_lines:
                while caption_lines and not caption_lines[-1].strip():
                    caption_lines.pop()
                return "\n".join(caption_lines).strip()

            return None

        except Exception as e:
            self.logger.error(f"メタデータファイルの読み込みエラー: {str(e)}")
            return None

    def _set_textarea_value_via_js(self, driver, el, text):
        """JavaScriptを使用してテキストエリアに値を設定（絵文字対応）"""
        b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
        script = r"""
            (function(el, b64){
              const bin = atob(b64);
              const bytes = new Uint8Array(bin.length);
              for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
              const text = new TextDecoder('utf-8').decode(bytes);
              el.value = text;
              el.dispatchEvent(new Event('input',  { bubbles: true }));
              el.dispatchEvent(new Event('change', { bubbles: true }));
            })(arguments[0], arguments[1]);
        """
        driver.execute_script(script, el, b64)

    def _fill_post_form(self, driver, description: str | None):
        """フォームに入力して投稿"""
        try:
            # キャプションが空でない場合のみ入力（空文字列やNoneはスキップ）
            if description and description.strip():
                self.logger.info(f"キャプションを入力します（{len(description)}文字）")
                description_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[jsname="YPqjbf"]'))
                )
                self.logger.info("Setting description via JS...")
                driver.execute_script("arguments[0].value='';", description_field)
                self._set_textarea_value_via_js(driver, description_field, description.strip())
                time.sleep(1)
            else:
                self.logger.info("キャプションが空のため、スキップします")

            # ボタンの追加セクションを探してクリック
            self.logger.info("Looking for button section...")
            button_dropdown = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[jscontroller="oIpQqb"]'))
            )
            button_dropdown.click()
            time.sleep(2)

            button_dropdown = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-haspopup="true"]'))
            )
            button_dropdown.click()
            time.sleep(2)

            # CALLオプションを選択（存在する場合のみ）
            try:
                self.logger.info("Trying to select CALL option...")
                call_option = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'li[value="CALL"]'))
                )
                call_option.click()
                self.logger.info("CALL option successfully selected")
                time.sleep(2)
            except Exception as call_error:
                self.logger.info(f"CALL option not found or not clickable: {call_error}")
                try:
                    button_dropdown.click()
                    time.sleep(2)
                except:
                    pass

            # 投稿ボタンをクリック
            self.logger.info("Clicking submit button...")
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[jsname="PtNcAd"]'))
            )
            submit_button.click()
            time.sleep(3)

            return True

        except Exception as e:
            self.logger.error(f"Error filling form: {e}")
            return False

    def upload_post_via_selenium(
        self,
        location_id: str,
        file_paths: list[str],
        metadata_path: str | None = None,
        caption: str | None = None,
    ) -> dict[str, Any]:
        """
        Seleniumを使用してGoogle Business Profileに投稿をアップロード

        Args:
            location_id: Google Business Profile のロケーションID
            file_paths: アップロードするファイルパスのリスト
            metadata_path: メタデータファイルのパス（キャプションを抽出するため）
            caption: キャプション（直接指定する場合、metadata_pathより優先）

        Returns:
            アップロード結果の辞書
        """
        try:
            # キャプションを取得
            if caption is None and metadata_path:
                caption = self._extract_caption_from_metadata(metadata_path)

            # GBP投稿画面を開く
            driver = self._create_business_post(location_id)
            if not driver:
                return {"success": False, "error": "投稿画面オープン失敗"}

            # メディアアップロード
            upload_success, last_file_path = self._upload_media_files(driver, file_paths)
            if not upload_success:
                self.logger.error("メディアアップロード失敗")
                driver.quit()
                return {"success": False, "error": "メディアアップロード失敗"}

            # フォーム入力と投稿
            if not self._fill_post_form(driver, caption):
                self.logger.error("フォーム送信失敗")
                driver.quit()
                return {"success": False, "error": "フォーム送信失敗"}

            # 投稿完了後の処理
            time.sleep(3)
            driver.quit()
            self.driver = None

            self.logger.info("Seleniumアップロード処理完了")
            return {
                "success": True,
                "location_id": location_id,
                "uploaded_files": file_paths,
                "caption": caption,
                "message": "Seleniumアップロード成功",
            }

        except Exception as e:
            self.logger.error(f"予期せぬエラー: {str(e)}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            return {"success": False, "error": str(e)}

    def cleanup(self):
        """リソースのクリーンアップ"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

