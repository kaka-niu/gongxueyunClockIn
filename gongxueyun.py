import subprocess
import sys
import json
import os

from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox

from ui.ui import Ui_Form


class MainWindow(QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # 中文 -> 英文打卡类型映射
        self.type_map = {
            "上班": "START",
            "下班": "END",
            "休息/节假日": "HOLIDAY"
        }

        # 绑定按钮
        self.saveInfo.clicked.connect(self.save_config)
        self.readInfo.clicked.connect(self.load_config)
        self.pushButton.clicked.connect(self.clock_in)

        # 监听地址相关输入，实时更新
        self.province.textChanged.connect(self.update_full_address)
        self.city.textChanged.connect(self.update_full_address)
        self.area.textChanged.connect(self.update_full_address)
        self.positioning.textChanged.connect(self.update_full_address)

    # ======================
    # 实时拼接详细地址
    # ======================
    def update_full_address(self):
        province = self.province.text().strip()
        city = self.city.text().strip()
        area = self.area.text().strip()
        detail = self.positioning.text().strip()

        if detail and not detail.endswith("附近"):
            detail = detail + "附近"

        parts = [p for p in [province, city, area, detail] if p]

        if parts:
            self.address.setText(" · ".join(parts))
        else:
            self.address.setText("详细地址：")

    # ======================
    # 获取 config 文件路径（根目录 user 文件夹）
    # ======================
    def get_config_path(self):
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        user_dir = os.path.join(base_dir, "user")
        os.makedirs(user_dir, exist_ok=True)
        return os.path.join(user_dir, "config.json")

    # ======================
    # 保存配置
    # ======================
    def save_config(self):
        phone = self.phone.text().strip()
        password = self.password.text().strip()

        province = self.province.text().strip()
        city = self.city.text().strip()
        area = self.area.text().strip()
        detail = self.positioning.text().strip()

        longitude = self.longitude.text().strip()
        latitude = self.latitude.text().strip()

        brand = self.brand.text().strip()
        platform = self.platform.text().strip()
        system_version = self.systemVersion.text().strip()
        incremental = self.incremental.text().strip()

        # 单选校验
        checked_button = self.buttonGroup.checkedButton()
        if not checked_button:
            QMessageBox.warning(self, "提示", "请选择打卡类型")
            return
        clock_type = self.type_map.get(checked_button.text(), "START")

        # 全量校验
        fields = {
            "账号": phone,
            "密码": password,
            "省份": province,
            "城市": city,
            "区县": area,
            "详细地址": detail,
            "经度": longitude,
            "纬度": latitude,
            "品牌型号": brand,
            "系统类型": platform,
            "系统版本": system_version,
            "型号代码": incremental
        }
        for name, value in fields.items():
            if not value:
                QMessageBox.warning(self, "提示", f"{name} 不能为空")
                return

        if not detail.endswith("附近"):
            detail += "附近"

        full_address = f"{province} · {city} · {area} · {detail}"
        device_str = (
            f"{{brand: {brand}, "
            f"systemVersion: {system_version}, "
            f"Platform: {platform}, "
            f"isPhysicalDevice: true, "
            f"incremental: {incremental}}}"
        )

        config_data = {
            "config": {
                "user": {
                    "phone": phone,
                    "password": password
                },
                "clockIn": {
                    "type": clock_type,
                    "location": {
                        "address": full_address,
                        "latitude": latitude,
                        "longitude": longitude,
                        "province": province,
                        "city": city,
                        "area": area
                    }
                },
                "device": device_str
            }
        }

        config_path = self.get_config_path()
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "成功", "配置信息已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败：\n{e}")

    # ======================
    # 读取配置
    # ======================
    def load_config(self):
        config_path = self.get_config_path()
        if not os.path.exists(config_path):
            QMessageBox.warning(self, "提示", "未找到 config.json")
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            cfg = data.get("config", {})
            user = cfg.get("user", {})
            clock = cfg.get("clockIn", {})
            location = clock.get("location", {})

            # 基础信息
            self.phone.setText(user.get("phone", ""))
            self.password.setText(user.get("password", ""))

            self.province.setText(location.get("province", ""))
            self.city.setText(location.get("city", ""))
            self.area.setText(location.get("area", ""))
            self.longitude.setText(location.get("longitude", ""))
            self.latitude.setText(location.get("latitude", ""))

            # 地址最后一段
            address = location.get("address", "")
            if "·" in address:
                last = address.split("·")[-1].strip()
                self.positioning.setText(last.replace("附近", ""))

            # 恢复单选
            reverse_map = {v: k for k, v in self.type_map.items()}  # 英文 -> 中文
            clock_type_en = clock.get("type", "")
            clock_type_ch = reverse_map.get(clock_type_en, "")
            for btn in self.buttonGroup.buttons():
                if btn.text() == clock_type_ch:
                    btn.setChecked(True)
                    break

            # 设备信息
            device = cfg.get("device", "")
            if device.startswith("{") and device.endswith("}"):
                body = device[1:-1]
                for part in body.split(","):
                    if ":" not in part:
                        continue
                    key, val = part.split(":", 1)
                    key = key.strip()
                    val = val.strip()
                    if key == "brand":
                        self.brand.setText(val)
                    elif key == "Platform":
                        self.platform.setText(val)
                    elif key == "systemVersion":
                        self.systemVersion.setText(val)
                    elif key == "incremental":
                        self.incremental.setText(val)

            QMessageBox.information(self, "成功", "配置已读取")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取失败：\n{e}")

    # ======================
    # 打卡事件（运行 main.py 或 main.exe）
    # ======================
    def clock_in(self):
        # 检查配置是否已读取
        if not self.phone.text().strip() or not self.password.text().strip():
            QMessageBox.warning(self, "提示", "请先读取配置信息")
            return

        checked_button = self.buttonGroup.checkedButton()
        if not checked_button:
            QMessageBox.warning(self, "提示", "请选择打卡类型")
            return

        clock_type = self.type_map.get(checked_button.text(), "START")
        latitude = self.latitude.text().strip()
        longitude = self.longitude.text().strip()
        address = self.address.text().strip()

        # 获取 base 目录
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

        # ========== 开发时使用 main.py ==========
        main_path = os.path.join(base_dir, "main.py")

        # ========== 打包后使用 main.exe ==========
        # main_path = os.path.join(base_dir, "main.exe")

        if not os.path.exists(main_path):
            QMessageBox.critical(self, "错误", f"未找到 {os.path.basename(main_path)}")
            return

        try:
            # Windows 下打开新的 cmd 窗口执行
            subprocess.Popen(
                f'start cmd /k "{main_path}"',
                shell=True,
                cwd=base_dir
            )
            QMessageBox.information(
                self, "提示",
                f"用户 {self.phone.text().strip()} 正在执行打卡任务\n已在新命令行窗口运行 {os.path.basename(main_path)}"
            )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行 {os.path.basename(main_path)} 失败：\n{e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
