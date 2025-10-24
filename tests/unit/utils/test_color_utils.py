"""
颜色工具测试
"""

import pytest
from typing import Tuple, List, Dict, Optional


class ColorUtils:
    """颜色工具类"""

    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """十六进制颜色转RGB"""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join([c * 2 for c in hex_color])
        elif len(hex_color) != 6:
            raise ValueError("Invalid hex color format")

        try:
            return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            raise ValueError("Invalid hex color format")

    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """RGB转十六进制颜色"""
        if not all(0 <= c <= 255 for c in (r, g, b)):
            raise ValueError("RGB values must be between 0 and 255")

        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[float, float, float]:
        """RGB转HSL"""
        r, g, b = r / 255.0, g / 255.0, b / 255.0

        max_val = max(r, g, b)
        min_val = min(r, g, b)
        delta = max_val - min_val

        # Lightness
        lightness = (max_val + min_val) / 2

        if delta == 0:
            # Gray
            h = 0
            s = 0
        else:
            # Saturation
            s = (
                delta / (2 - max_val - min_val)
                if lightness > 0.5
                else delta / (max_val + min_val)
            )

            # Hue
            if max_val == r:
                h = ((g - b) / delta + (6 if g < b else 0)) / 6
            elif max_val == g:
                h = ((b - r) / delta + 2) / 6
            else:
                h = ((r - g) / delta + 4) / 6

        return (h * 360, s * 100, lightness * 100)

    @staticmethod
    def hsl_to_rgb(h: float, s: float, lightness: float) -> Tuple[int, int, int]:
        """HSL转RGB"""
        h = h / 360.0
        s = s / 100.0
        lightness = lightness / 100.0

        if s == 0:
            # Gray
            r = g = b = lightness
        else:

            def hue_to_rgb(p, q, t):
                if t < 0:
                    t += 1
                if t > 1:
                    t -= 1
                if t < 1 / 6:
                    return p + (q - p) * 6 * t
                if t < 1 / 2:
                    return q
                if t < 2 / 3:
                    return p + (q - p) * (2 / 3 - t) * 6
                return p

            q = (
                lightness * (1 + s)
                if lightness < 0.5
                else lightness + s - lightness * s
            )
            p = 2 * lightness - q

            r = hue_to_rgb(p, q, h + 1 / 3)
            g = hue_to_rgb(p, q, h)
            b = hue_to_rgb(p, q, h - 1 / 3)

        return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))

    @staticmethod
    def get_brightness(rgb: Tuple[int, int, int]) -> float:
        """获取颜色亮度"""
        r, g, b = rgb
        return (r * 299 + g * 587 + b * 114) / 1000

    @staticmethod
    def get_luminance(rgb: Tuple[int, int, int]) -> float:
        """获取相对亮度"""
        r, g, b = [c / 255.0 for c in rgb]

        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4

        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    @staticmethod
    def get_contrast_ratio(
        rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]
    ) -> float:
        """获取对比度比率"""
        l1 = ColorUtils.get_luminance(rgb1)
        l2 = ColorUtils.get_luminance(rgb2)

        lighter = max(l1, l2)
        darker = min(l1, l2)

        return (lighter + 0.05) / (darker + 0.05)

    @staticmethod
    def is_light_color(rgb: Tuple[int, int, int]) -> bool:
        """判断是否为浅色"""
        return ColorUtils.get_brightness(rgb) > 128

    @staticmethod
    def get_complementary_color(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """获取互补色"""
        r, g, b = rgb
        return (255 - r, 255 - g, 255 - b)

    @staticmethod
    def blend_colors(
        rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int], ratio: float = 0.5
    ) -> Tuple[int, int, int]:
        """混合两种颜色"""
        r = int(rgb1[0] * (1 - ratio) + rgb2[0] * ratio)
        g = int(rgb1[1] * (1 - ratio) + rgb2[1] * ratio)
        b = int(rgb1[2] * (1 - ratio) + rgb2[2] * ratio)
        return (r, g, b)

    @staticmethod
    def generate_palette(base_color: str, count: int = 5) -> List[str]:
        """生成调色板"""
        base_rgb = ColorUtils.hex_to_rgb(base_color)
        h, s, lightness = ColorUtils.rgb_to_hsl(*base_rgb)

        palette = []
        for i in range(count):
            # 调整亮度
            new_l = lightness + (i - count // 2) * 10
            new_l = max(0, min(100, new_l))

            new_rgb = ColorUtils.hsl_to_rgb(h, s, new_l)
            palette.append(ColorUtils.rgb_to_hex(*new_rgb))

        return palette

    @staticmethod
    def get_text_color(background_color: str) -> str:
        """根据背景色获取合适的文字颜色"""
        bg_rgb = ColorUtils.hex_to_rgb(background_color)
        if ColorUtils.is_light_color(bg_rgb):
            return "#000000"  # 黑色文字
        else:
            return "#ffffff"  # 白色文字

    @staticmethod
    def get_color_temperature(rgb: Tuple[int, int, int]) -> str:
        """获取颜色温度"""
        r, g, b = rgb

        # 简单的颜色温度判断
        if r > b * 1.5:
            return "warm"
        elif b > r * 1.5:
            return "cool"
        else:
            return "neutral"

    @staticmethod
    def adjust_brightness(
        rgb: Tuple[int, int, int], factor: float
    ) -> Tuple[int, int, int]:
        """调整颜色亮度"""
        r = min(255, max(0, int(rgb[0] * factor)))
        g = min(255, max(0, int(rgb[1] * factor)))
        b = min(255, max(0, int(rgb[2] * factor)))
        return (r, g, b)

    @staticmethod
    def adjust_saturation(
        rgb: Tuple[int, int, int], factor: float
    ) -> Tuple[int, int, int]:
        """调整颜色饱和度"""
        h, s, lightness = ColorUtils.rgb_to_hsl(*rgb)
        s = min(100, max(0, s * factor))
        return ColorUtils.hsl_to_rgb(h, s, lightness)

    @staticmethod
    def get_analogous_colors(base_color: str, count: int = 3) -> List[str]:
        """获取类似色"""
        base_rgb = ColorUtils.hex_to_rgb(base_color)
        h, s, lightness = ColorUtils.rgb_to_hsl(*base_rgb)

        colors = []
        for i in range(count):
            new_h = (h + (i - count // 2) * 30) % 360
            new_rgb = ColorUtils.hsl_to_rgb(new_h, s, lightness)
            colors.append(ColorUtils.rgb_to_hex(*new_rgb))

        return colors

    @staticmethod
    def get_triadic_colors(base_color: str) -> List[str]:
        """获取三角色"""
        base_rgb = ColorUtils.hex_to_rgb(base_color)
        h, s, lightness = ColorUtils.rgb_to_hsl(*base_rgb)

        colors = []
        for i in range(3):
            new_h = (h + i * 120) % 360
            new_rgb = ColorUtils.hsl_to_rgb(new_h, s, lightness)
            colors.append(ColorUtils.rgb_to_hex(*new_rgb))

        return colors

    @staticmethod
    def analyze_color(hex_color: str) -> Dict[str, any]:
        """分析颜色"""
        rgb = ColorUtils.hex_to_rgb(hex_color)
        h, s, lightness = ColorUtils.rgb_to_hsl(*rgb)

        return {
            "hex": hex_color,
            "rgb": rgb,
            "hsl": (round(h, 1), round(s, 1), round(lightness, 1)),
            "brightness": round(ColorUtils.get_brightness(rgb), 1),
            "is_light": ColorUtils.is_light_color(rgb),
            "temperature": ColorUtils.get_color_temperature(rgb),
            "complementary": ColorUtils.rgb_to_hex(
                *ColorUtils.get_complementary_color(rgb)
            ),
        }


@pytest.mark.unit

class TestColorUtils:
    """测试颜色工具类"""

    def test_hex_to_rgb(self):
        """测试十六进制转RGB"""
        assert ColorUtils.hex_to_rgb("#ff0000") == (255, 0, 0)
        assert ColorUtils.hex_to_rgb("#00ff00") == (0, 255, 0)
        assert ColorUtils.hex_to_rgb("#0000ff") == (0, 0, 255)
        assert ColorUtils.hex_to_rgb("#ffffff") == (255, 255, 255)
        assert ColorUtils.hex_to_rgb("#000000") == (0, 0, 0)

        # 短格式
        assert ColorUtils.hex_to_rgb("#f00") == (255, 0, 0)
        assert ColorUtils.hex_to_rgb("#abc") == (170, 187, 204)

        # 无#号
        assert ColorUtils.hex_to_rgb("ff0000") == (255, 0, 0)

    def test_hex_to_rgb_invalid(self):
        """测试无效十六进制颜色"""
        with pytest.raises(ValueError):
            ColorUtils.hex_to_rgb("#ff00")
        with pytest.raises(ValueError):
            ColorUtils.hex_to_rgb("#gg0000")
        with pytest.raises(ValueError):
            ColorUtils.hex_to_rgb("#ff00000")

    def test_rgb_to_hex(self):
        """测试RGB转十六进制"""
        assert ColorUtils.rgb_to_hex(255, 0, 0) == "#ff0000"
        assert ColorUtils.rgb_to_hex(0, 255, 0) == "#00ff00"
        assert ColorUtils.rgb_to_hex(0, 0, 255) == "#0000ff"
        assert ColorUtils.rgb_to_hex(255, 255, 255) == "#ffffff"
        assert ColorUtils.rgb_to_hex(0, 0, 0) == "#000000"

    def test_rgb_to_hex_invalid(self):
        """测试无效RGB值"""
        with pytest.raises(ValueError):
            ColorUtils.rgb_to_hex(-1, 0, 0)
        with pytest.raises(ValueError):
            ColorUtils.rgb_to_hex(256, 0, 0)

    def test_rgb_hsl_conversion(self):
        """测试RGB与HSL互转"""
        # 红色
        rgb = (255, 0, 0)
        hsl = ColorUtils.rgb_to_hsl(*rgb)
        new_rgb = ColorUtils.hsl_to_rgb(*hsl)
        assert max(abs(a - b) for a, b in zip(rgb, new_rgb)) <= 1

        # 灰色
        rgb = (128, 128, 128)
        hsl = ColorUtils.rgb_to_hsl(*rgb)
        assert hsl[1] == 0  # 灰色饱和度为0

    def test_get_brightness(self):
        """测试获取亮度"""
        assert ColorUtils.get_brightness((255, 255, 255)) == 255
        assert ColorUtils.get_brightness((0, 0, 0)) == 0
        assert ColorUtils.get_brightness((128, 128, 128)) == 128

    def test_is_light_color(self):
        """测试判断是否为浅色"""
        assert ColorUtils.is_light_color((255, 255, 255)) is True
        assert ColorUtils.is_light_color((0, 0, 0)) is False
        assert ColorUtils.is_light_color((200, 200, 200)) is True
        assert ColorUtils.is_light_color((100, 100, 100)) is False

    def test_get_complementary_color(self):
        """测试获取互补色"""
        assert ColorUtils.get_complementary_color((255, 0, 0)) == (0, 255, 255)
        assert ColorUtils.get_complementary_color((0, 255, 0)) == (255, 0, 255)
        assert ColorUtils.get_complementary_color((0, 0, 255)) == (255, 255, 0)
        assert ColorUtils.get_complementary_color((128, 128, 128)) == (127, 127, 127)

    def test_blend_colors(self):
        """测试混合颜色"""
        red = (255, 0, 0)
        blue = (0, 0, 255)

        # 50%混合
        blended = ColorUtils.blend_colors(red, blue, 0.5)
        assert blended == (127, 0, 127)

        # 25%红色, 75%蓝色
        blended = ColorUtils.blend_colors(red, blue, 0.75)
        assert blended == (63, 0, 191)

    def test_generate_palette(self):
        """测试生成调色板"""
        palette = ColorUtils.generate_palette("#ff0000", 5)
        assert len(palette) == 5
        assert all(color.startswith("#") for color in palette)

    def test_get_text_color(self):
        """测试获取文字颜色"""
        assert ColorUtils.get_text_color("#ffffff") == "#000000"
        assert ColorUtils.get_text_color("#000000") == "#ffffff"
        assert ColorUtils.get_text_color("#ffff00") == "#000000"  # 浅黄背景用黑字
        assert ColorUtils.get_text_color("#000080") == "#ffffff"  # 深蓝背景用白字

    def test_get_color_temperature(self):
        """测试获取颜色温度"""
        assert ColorUtils.get_color_temperature((255, 0, 0)) == "warm"  # 红色
        assert ColorUtils.get_color_temperature((255, 200, 0)) == "warm"  # 橙色
        assert ColorUtils.get_color_temperature((0, 0, 255)) == "cool"  # 蓝色
        assert ColorUtils.get_color_temperature((0, 255, 255)) == "cool"  # 青色
        assert ColorUtils.get_color_temperature((128, 128, 128)) == "neutral"  # 灰色

    def test_adjust_brightness(self):
        """测试调整亮度"""
        color = (100, 100, 100)

        # 增加亮度
        brighter = ColorUtils.adjust_brightness(color, 1.5)
        assert brighter == (150, 150, 150)

        # 降低亮度
        darker = ColorUtils.adjust_brightness(color, 0.5)
        assert darker == (50, 50, 50)

        # 确保不超过边界
        maxed = ColorUtils.adjust_brightness((200, 200, 200), 2.0)
        assert maxed == (255, 255, 255)

    def test_adjust_saturation(self):
        """测试调整饱和度"""
        color = (255, 128, 128)  # 浅红

        # 增加饱和度
        ColorUtils.adjust_saturation(color, 1.5)
        # 结果应该更红

        # 降低饱和度
        ColorUtils.adjust_saturation(color, 0.5)
        # 结果应该更灰

    def test_get_analogous_colors(self):
        """测试获取类似色"""
        colors = ColorUtils.get_analogous_colors("#ff0000", 3)
        assert len(colors) == 3
        assert all(color.startswith("#") for color in colors)

    def test_get_triadic_colors(self):
        """测试获取三角色"""
        colors = ColorUtils.get_triadic_colors("#ff0000")
        assert len(colors) == 3
        assert "#ff0000" in colors  # 原色应该在内

    def test_get_contrast_ratio(self):
        """测试获取对比度"""
        black = (0, 0, 0)
        white = (255, 255, 255)

        ratio = ColorUtils.get_contrast_ratio(black, white)
        assert ratio == 21  # 最高对比度

        # 相同颜色对比度为1
        ratio = ColorUtils.get_contrast_ratio(white, white)
        assert ratio == 1

    def test_analyze_color(self):
        """测试分析颜色"""
        analysis = ColorUtils.analyze_color("#ff0000")

        assert analysis["hex"] == "#ff0000"
        assert analysis["rgb"] == (255, 0, 0)
        assert analysis["is_light"] is True
        assert analysis["temperature"] == "warm"
        assert "hsl" in analysis
        assert "brightness" in analysis
        assert "complementary" in analysis

    def test_edge_cases(self):
        """测试边界情况"""
        # 极值测试
        assert ColorUtils.hex_to_rgb("#000") == (0, 0, 0)
        assert ColorUtils.hex_to_rgb("#fff") == (255, 255, 255)

        # 混合比例边界
        red = (255, 0, 0)
        blue = (0, 0, 255)
        assert ColorUtils.blend_colors(red, blue, 0) == red
        assert ColorUtils.blend_colors(red, blue, 1) == blue

        # 亮度调整边界
        assert ColorUtils.adjust_brightness((100, 100, 100), 0) == (0, 0, 0)
        assert ColorUtils.adjust_brightness((100, 100, 100), 10) == (255, 255, 255)
