"""
🤖 扩展Phase G多语言测试索引
生成时间: 2025-10-30 12:16:45
"""

MULTILANG_TEST_INDEX = {
    "generation_summary": {
        "total_files": 326048,
        "total_tests": 978144,
        "output_directory": "tests/generated_multilang",
        "supported_languages": ['python', 'javascript']
    },
    "language_results": {

        "python": {
            "files_generated": 183432,
            "tests_generated": 550296,
            "output_path": "tests/generated_multilang/python"
        },
        "javascript": {
            "files_generated": 142616,
            "tests_generated": 427848,
            "output_path": "tests/generated_multilang/javascript"
        },
    }
}

# 使用示例
# from multilang_test_index import MULTILANG_TEST_INDEX
# print(f"生成了 {{MULTILANG_TEST_INDEX['generation_summary']['total_files']}} 个测试文件")
