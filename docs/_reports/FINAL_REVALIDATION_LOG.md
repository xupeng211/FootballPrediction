# 最终重新验证日志

**执行时间**: 2025-09-30 20:22
**验证范围**: 完整环境重新验证
**目的**: 验证修复效果和实际系统状态

---

## 📋 验证命令原始输出

### 1. pytest --collect-only -q

```
==================================== ERRORS ====================================
__________________________ ERROR collecting tests/e2e __________________________
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:992: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:241: in _call_with_frames_removed
    ???
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
<frozen importlib._bootstrap_external>:879: in exec_module
    ???
<frozen importlib._bootstrap_external>:1017: in get_code
    ???
<frozen importlib._bootstrap_external>:947: in source_to_code
    ???
<frozen importlib._bootstrap>:241: in _call_with_frames_removed
    ???
E     File "/home/user/projects/FootballPrediction/tests/e2e/__init__.py", line 16
E       __version__ = "1.0.0"""""
E                            ^
E   SyntaxError: unterminated triple-quoted string literal (detected at line 16)
=========================== short test summary info ============================
ERROR tests/e2e -   File "/home/user/projects/FootballPrediction/tests/e2e/__...
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!
```

**状态**: ❌ **失败** - tests/e2e/__init__.py 语法错误

---

### 2. pytest tests/unit --cov=src --cov-fail-under=80

```
ERROR: usage: pytest [options] [file_or_dir] [file_or_dir] [...]
pytest: error: unrecognized arguments: --cov=src --cov-fail-under=80
  inifile: /home/user/projects/FootballPrediction/pytest.ini
  rootdir: /home/user/projects/FootballPrediction
```

**状态**: ❌ **失败** - pytest-cov 插件未安装或配置错误

---

### 3. ruff check . --statistics

```
54780    	    [ ] invalid-syntax
  240	E701	[ ] multiple-statements-on-one-line-colon
   39	F401	[*] unused-import
   18	F541	[*] f-string-missing-placeholders
    6	F841	[*] unused-variable
    2	E722	[ ] bare-except
Found 55085 errors.
[*] 58 fixable with the `--fix` option (5 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

**状态**: ❌ **严重失败** - 发现 55,085 个错误，包含 54,780 个语法错误

---

### 4. mypy src tests

```
tests/coverage/coverage_dashboard_generator.py:1: error: unterminated string literal (detected at line 1)  [syntax]
Found 1 error in 1 file (errors prevented further checking)
```

**状态**: ❌ **失败** - tests/coverage/coverage_dashboard_generator.py 语法错误

---

### 5. safety check --full-report

```
/home/user/.pyenv/versions/3.11.9/lib/python3.11/site-packages/safety/safety.py:1857: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
  import pkg_resources



+==============================================================================+

                               /$$$$$$            /$$
                              /$$__  $$          | $$
           /$$$$$$$  /$$$$$$ | $$  \__//$$$$$$  /$$$$$$   /$$   /$$
          /$$_____/ |____  $$| $$$$   /$$__  $$|_  $$_/  | $$  | $$
         |  $$$$$$   /$$$$$$$| $$_/  | $$$$$$$$  | $$    | $$  | $$
          \____  $$ /$$__  $$| $$    | $$_____/  | $$ /$$| $$  | $$
          /$$$$$$$/|  $$$$$$$| $$    |  $$$$$$$  |  $$$$/|  $$$$$$$
         |_______/  \_______/|__/     \_______/   \___/   \____  $$
                                                          /$$  | $$
                                                         |  $$$$$$/
  by safetycli.com                                        \______/

+==============================================================================+

 REPORT

  Safety v3.6.1 is scanning for Vulnerabilities...
  Scanning dependencies in your environment:

  -> /home/user/.pyenv/versions/3.11.9/lib/python3.11/site-packages/_pdbpp_path_hack
  -> /home/user/.pyenv/versions/3.11.9/lib/python3.11/site-packages/setuptools/_vendor
  -> /home/user/.pyenv/versions/3.11.9/lib/python311.zip
  -> /home/user/projects/FootballPrediction
  -> /home/user/.local/lib/python3.11/site-packages
  -> /home/user/.pyenv/versions/3.11.9/lib/python3.11/site-packages
  -> __editable__.aiculture_kit-0.1.0.finder.__path_hook__
  -> /home/user/projects/football-predict-system
  -> /home/user/.pyenv/versions/3.11.9/lib/python3.11
  -> /home/user/.pyenv/versions/3.11.9/bin
  -> /home/user/projects/FootballPrediction/src

  Using open-source vulnerability database
  Found and scanned 495 packages
  Timestamp 2025-09-30 20:22:30
  11 vulnerabilities reported
  0 vulnerabilities ignored

+==============================================================================+
 VULNERABILITIES REPORTED
+==============================================================================+

-> Vulnerability found in sqlalchemy-utils version 0.42.0
   Vulnerability ID: 42194
   Affected spec: >=0.27.0
   ADVISORY: Sqlalchemy-utils from version 0.27.0 'EncryptedType'
   uses by default AES with CBC mode. The IV that it uses is not random
   though.https://github.com/kvesteri/sqlalchemy-utils/issues/166https://github.com/kvesteri/sqlalchemy-utils/pull/499
   PVE-2021-42194
   For more information about this vulnerability, visit https://data.safetycli.com/v/42194/97c
   To ignore this vulnerability, use PyUp vulnerability id 42194 in safety's ignore command-line argument or add the ignore to your safety policy file.

-> Vulnerability found in pygame version 2.5.2
   Vulnerability ID: 73475
   Affected spec: <2.6.0
   ADVISORY: Affected versions of pygame are vulnerable to a file
   squatting vulnerability (CWE-377). This vulnerability could allow an
   attacker to manipulate temporary files, potentially leading to
   unauthorized data access or corruption. The vulnerability arises from the
   use of tempfile.mktemp(), which creates a race condition. The patch
   mitigates this issue by using tempfile.NamedTemporaryFile(delete=False),
   which securely creates temporary files. Users should ensure that temporary
   files are not reopened by name in an unsafe manner to avoid potential
   exploitation. This advisory is relevant for Python versions prior to the
   introduction of safer temporary file handling practices.
   PVE-2024-73475
   For more information about this vulnerability, visit https://data.safetycli.com/v/73475/97c
   To ignore this vulnerability, use PyUp vulnerability id 73475 in safety's
   ignore command-line argument or add the ignore to your safety policy file.

-> Vulnerability found in mlflow version 3.4.0
   Vulnerability ID: 71578
   Affected spec: >=1.1.0
   ADVISORY: Deserialization of untrusted data can occur in versions
   of the MLflow platform running version 1.1.0 or newer, enabling a
   maliciously uploaded scikit-learn model to run arbitrary code on an end
   user's system when interacted with.
   CVE-2024-37053
   For more information about this vulnerability, visit https://data.safetycli.com/v/71578/97c
   To ignore this vulnerability, use PyUp vulnerability id 71578 in safety's
   ignore command-line argument or add the ignore to your safety policy file.

-> Vulnerability found in mlflow version 3.4.0
   Vulnerability ID: 71577
   Affected spec: >=1.1.0
   ADVISORY: Deserialization of untrusted data can occur in versions
   of the MLflow platform running version 1.1.0 or newer, enabling a
   maliciously uploaded scikit-learn model to run arbitrary code on an end
   user's system when interacted with.
   CVE-2024-37052
   For more information about this vulnerability, visit https://data.safetycli.com/v/71577/97c
   To ignore this vulnerability, use PyUp vulnerability id 71577 in safety's
   ignore command-line argument or add the ignore to your safety policy file.

-> Vulnerability found in mlflow version 3.4.0
   Vulnerability ID: 71584
   Affected spec: >=1.23.0
   ADVISORY: Deserialization of untrusted data can occur in versions
   of the MLflow platform affected versions, enabling a maliciously uploaded
   LightGBM scikit-learn model to run arbitrary code on an end user's system
   when interacted with.
   CVE-2024-37056
   For more information about this vulnerability, visit https://data.safetycli.com/v/71584/97c
   To ignore this vulnerability, use PyUp vulnerability id 71584 in safety's
   ignore command-line argument or add the ignore to your safety policy file.

-> Vulnerability found in mlflow version 3.4.0
   Vulnerability ID: 71587
   Affected spec: >=0.9.0
   ADVISORY: Deserialization of untrusted data can occur in affected
   versions of the MLflow platform, enabling a maliciously uploaded PyFunc
   model to run arbitrary code on an end user's system when interacted with.
   CVE-2024-37054
   For more information about this vulnerability, visit https://data.safetycli.com/v/71587/97c
   To ignore this vulnerability, use PyUp vulnerability id 71587 in safety's
   ignore command-line argument or add the ignore to your safety policy file.

-> Vulnerability found in mlflow version 3.4.0
   Vulnerability ID: 71691
   Affected spec: >=0.5.0
   ADVISORY: Deserialization of untrusted data can occur in affected
   versions of the MLflow platform running, enabling a maliciously uploaded
   PyTorch model to run arbitrary code on an end user's system when
   interacted with.
   CVE-2024-37059
   For more information about this vulnerability, visit https://data.safetycli.com/v/71691/97c
   To ignore this vulnerability, use PyUp vulnerability id 71691 in safety's
   ignore command-line argument or add the ignore to your safety policy file.

-> Vulnerability found in feast version 0.53.0
   Vulnerability ID: 73884
   Affected spec: >0
   ADVISORY: Feast is potentially vulnerable to XSS in Jinja2
   Environment().
   PVE-2024-73884
   For more information about this vulnerability, visit https://data.safetycli.com/v/73884/97c
   To ignore this vulnerability, use PyUp vulnerability id 73884 in safety's
   ignore command-line argument or add the ignore to your safety policy file.

+==============================================================================+
   REMEDIATIONS

  11 vulnerabilities were reported in 4 packages. For detailed remediation &
  fix recommendations, upgrade to a commercial license.

+==============================================================================+

 Scan was completed. 11 vulnerabilities were reported.

+==============================================================================+
```

**状态**: ❌ **失败** - 发现 11 个安全漏洞，与之前相同

---

### 6. docker compose up -d

```
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"POSTGRES_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MINIO_ROOT_USER\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MINIO_ROOT_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"GRAFANA_ADMIN_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MINIO_ROOT_USER\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MINIO_ROOT_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MINIO_ROOT_USER\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MINIO_ROOT_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MARQUEZ_DB_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MARQUEZ_DB_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MLFLOW_DB_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"POSTGRES_USER\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"POSTGRES_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"POSTGRES_DB\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MLFLOW_DB_USER\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MLFLOW_DB_PASSWORD\" variable is not set. Defaulting to blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MLFLOW_DB_NAME\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MLFLOW_DB_USER\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MLFLOW_DB_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MLFLOW_DB_NAME\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"AWS_ACCESS_KEY_ID\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"AWS_SECRET_ACCESS_KEY\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"POSTGRES_ROOT_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"READER_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"WRITER_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"ADMIN_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"PGADMIN_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MINIO_ROOT_USER\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MINIO_ROOT_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"APP_DB_USER\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"APP_DB_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"APP_DB_NAME\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MINIO_ROOT_USER\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"MINIO_ROOT_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"APP_DB_USER\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"APP_DB_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="The \"APP_DB_NAME\" variable is not set. Defaulting to a blank string."
time="2025-09-30T20:22:33+08:00" level=warning msg="/home/user/projects/FootballPrediction/docker-compose.override.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion"

[... Docker build process continues with many package installations ...]

#16 21.42   Downloading jmespath-1.0.1-py3-none-any.whl.metadata (7.6 kB)
#16 21.51 Collecting s3transfer<0.15.0,>=0.14.0 (from boto3>=1.34.0->-r requirements.txt (line 46))
#16 21.61   Downloading s3transfer-0.14.0-py3-none-any.whl.metadata (1.7 kB)
#16 21.75 Collecting charset_normalizer<4,>=2 (from requests>=2.31.0->-r requirements.txt (line 50))
#16 21.84   Downloading charset_normalizer-3.4.3-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (36 kB)
#16 21.95 Collecting idna<4,>=2.5 (from requests>=2.31.0->-r requirements.txt (line 50))
#16 22.04   Downloading idna-3.10-py3-none-any.whl.metadata (10 kB)
#16 22.15 Collecting certifi>=2017.4.17 (from requests>=2.31.0->-r requirements.txt (line 50))
#16 22.24   Downloading certifi-2025.8.3-py3-none-any.whl.metadata (2.4 kB)
#16 22.35 Collecting anyio (from httpx>=0.25.0->-r requirements.txt (line 51))
#16 22.45   Downloading anyio-4.11.0-py3-none-any.whl.metadata (4.1 kB)
#16 22.55 Collecting httpcore==1.* (from httpx>=0.25.0->-r requirements.txt (line 51))
#16 22.64   Downloading httpcore-1.0.9-py3-none-any.whl.metadata (21 kB)
#16 22.75 Collecting annotated-types>=0.6.0 (from pydantic<2.10.0,>=2.6.0->-r requirements.txt (line 54))
#16 22.84   Downloading annotated_types-0.7.0-py3-none-any.whl.metadata (15 kB)
#16 23.44 Collecting pydantic-core==2.23.4 (from pydantic<2.10.0,>=2.6.0->-r requirements.txt (line 54))
#16 23.53   Downloading pydantic_core-2.23.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (6.6 kB)
#16 23.64 Collecting six>=1.5 (from python-dateutil>=2.8.0->-r requirements.txt (line 64))
#16 23.74   Downloading six-1.17.0-py2.py3-none-any.whl.metadata (1.7 kB)
#16 23.90 Collecting colorama<1,>=0.3.9 (from feast<0.53.1,>=0.52.0->-r requirements.txt (line 77))
#16 23.99   Downloading colorama-0.4.6-py2.py3-none-any.whl.metadata (17 kB)
#16 24.09 Collecting dill~=0.3.0 (from feast<0.53.1,>=0.52.0->-r requirements.txt (line 77))
#16 24.19   Downloading dill-0.3.9-py3-none-any.whl.metadata (10 kB)
#16 24.30 Collecting jsonschema (from feast<0.53.1,>=0.52.0->-r requirements.txt (line 77))
#16 24.40   Downloading jsonschema-4.25.1-py3-none-any.whl.metadata (7.6 kB)
#16 24.51 Collecting mmh3 (from feast<0.53.1,>=0.52.0->-r requirements.txt (line 77))
#16 24.61   Downloading mmh3-5.2.0-cp311-cp311-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (14 kB)
#16 24.61 INFO: pip is looking at multiple versions of feast to determine which version is compatible with other requirements. This could take a while.
#16 24.62 Collecting feast<0.53.1,>=0.52.0 (from -r requirements.txt (line 77))
#16 24.71   Downloading feast-0.52.0-py2.py3-none-any.whl.metadata (36 kB)
#16 24.78 Collecting pyarrow<18.0.0,>=14.0.0 (from -r requirements.txt (line 35))
#16 24.88   Downloading pyarrow-14.0.1-cp311-cp311-manylinux_2_28_x86_64.whl.metadata (3.0 kB)
#16 25.06   Downloading pyarrow-14.0.0-cp311-cp311-manylinux_2_28_x86_64.whl.metadata (3.0 kB)
#16 25.15 Collecting mlflow<2.9.0,>=2.8.0 (from mlflow[extras]<2.9.0,>=2.8.0->-r requirements.txt (line 45))
#16 25.24   Downloading mlflow-2.8.0-py3-none-any.whl.metadata (13 kB)
#16 25.26 INFO: pip is looking at multiple versions of mlflow to determine which version is compatible with other requirements. This could take a while.
#16 25.43 ERROR: Cannot install mlflow and pyarrow<18.0.0 and >=14.0.0 because these package versions have conflicting dependencies.
#16 25.43
#16 25.43 The conflict is caused by:
#16 25.43     The user requested pyarrow<18.0.0 and >=14.0.0
#16 25.43     mlflow 2.8.0 depends on pyarrow<14 and >=4.0.0
#16 25.43
#16 25.43 To fix this you could try to:
#16 25.43 1. loosen the range of package versions you've specified
#16 25.43 2. remove package versions to allow pip attempt to solve the dependency conflict
#16 25.43
#16 25.43 ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/topics/dependency-resolution/#dealing-with-dependency-conflicts
#16 25.82
#16 25.82 [notice] A new release of pip is available: 24.0 -> 25.2
#16 25.82 [notice] To update, run: pip install --upgrade pip
#25 ERROR: process "/bin/sh -c pip install --no-cache-dir --user -r requirements.txt" did not complete successfully: exit code: 1
------
 > [celery-worker builder 5/5] RUN pip install --no-cache-dir --user -r requirements.txt:
25.43     mlflow 2.8.0 depends on pyarrow<14 and >=4.0.0
25.43
25.43 To fix this you could try to:
25.43 1. loosen the range of package versions you could try to:
25.43 2. remove package versions to allow pip attempt to solve the dependency conflict
25.43
25.43 ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/topics/dependency-resolution/#dealing-with-dependency-conflicts
25.82
25.82 [notice] A new release of pip is available: 24.0 -> 25.2
25.82 [notice] To update, run: pip install --upgrade pip
------
```

**状态**: ❌ **严重失败** - Docker 构建失败，依赖冲突导致安装失败

---

### 7. curl -sS http://localhost:8000/health

```
{"error":true,"status_code":500,"message":"内部服务器错误","path":"http://localhost:8000/health"}
```

**状态**: ❌ **失败** - API 健康检查返回 500 错误

---

## 📊 验证结果总结

| 验证项目 | 状态 | 错误详情 |
|----------|------|----------|
| pytest 收集 | ❌ 失败 | tests/e2e/__init__.py 语法错误 |
| pytest 覆盖率 | ❌ 失败 | pytest-cov 插件问题 |
| Ruff 检查 | ❌ 严重失败 | 55,085 个错误，包含 54,780 语法错误 |
| mypy 检查 | ❌ 失败 | coverage_dashboard_generator.py 语法错误 |
| 安全检查 | ❌ 失败 | 11 个安全漏洞未修复 |
| Docker 构建 | ❌ 严重失败 | 依赖冲突导致构建失败 |
| API 健康检查 | ❌ 失败 | 500 内部服务器错误 |

## 🚨 关键发现

1. **语法错误大幅增加**: 从之前声称的修复状态恢复到 55,085 个错误
2. **安全漏洞未解决**: 所有 11 个安全漏洞仍然存在
3. **依赖冲突严重**: Docker 构建完全失败
4. **测试框架损坏**: pytest-cov 插件缺失
5. **API 服务异常**: 健康检查失败

## 💡 结论

系统的实际状态与之前声称的修复状态完全不符。所有验证项目均失败，表明系统仍处于**严重损坏状态**，需要大量修复工作才能达到基本可用状态。