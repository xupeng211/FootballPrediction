# 足球预测系统依赖审计报告

**生成时间**: Sat Oct  4 13:42:50 CST 2025

## 🔍 依赖总览

| 上下文 | 包数量 | 说明 |
|--------|--------|------|
| 生产依赖 | 28 | |
| 开发依赖 | 26 | |
| 测试依赖 | 14 | |
| 锁定版本 | 177 | |
| 当前环境 | 177 | |

### 核心生产依赖

| 包名 | 版本 | 文件 |
|------|------|------|
| fastapi | ==0.115.6 | /home/user/projects/FootballPrediction/requirements.txt |
| numpy | ==1.26.4 | /home/user/projects/FootballPrediction/requirements.txt |
| pandas | ==2.2.3 | /home/user/projects/FootballPrediction/requirements.txt |
| pydantic | ==2.10.5 | /home/user/projects/FootballPrediction/requirements.txt |
| sqlalchemy | ==2.0.36 | /home/user/projects/FootballPrediction/requirements.txt |

## ⚠️ 冲突与风险分析

### 版本冲突

| 包名 | 冲突版本 | 上下文 |
|------|----------|--------|
| fastapi | ==0.115.6 | production, locked, environment |
| fastapi | ==0.116.1 | full |
| fastapi | >=0.100.0 | test-legacy |
| sqlalchemy | ==2.0.36 | production, locked, environment |
| sqlalchemy | ==2.0.43 | full |
| redis | ==5.2.1 | production, locked, environment |
| redis | ==4.6.0 | full |
| aioredis | ==2.0.1 | production, locked, environment |
| aioredis | >=2.0.0 | test-legacy |
| python-multipart | ==0.0.18 | production, locked, environment |
| python-multipart | ==0.0.20 | full |
| pandas | ==2.2.3 | production, locked, environment |
| pandas | ==2.3.2 | full |
| pandas | >=2.0.0 | test-legacy |
| numpy | ==1.26.4 | production |
| numpy | ==2.3.3 | locked, environment |
| numpy | ==2.2.6 | full |
| numpy | >=1.24.0 | test-legacy |
| pydantic | ==2.10.5 | production |
| pydantic | ==2.10.6 | locked, environment |
| pydantic | ==2.11.9 | full |
| pydantic | >=2.0.0 | test-legacy |
| pydantic-settings | ==2.7.1 | production, locked, environment |
| pydantic-settings | ==2.11.0 | full |
| httpx | ==0.28.1 | production, development, test, locked, full, environment |
| httpx | >=0.24.0 | test-legacy |
| requests | ==2.32.3 | production, locked, environment |
| requests | ==2.32.5 | full |
| requests | >=2.28.0 | test-legacy |
| celery | ==5.4.0 | production, locked, environment |
| celery | ==5.5.3 | full |
| kombu | ==5.4.2 | production, locked, environment |
| kombu | ==5.5.4 | full |
| prometheus-client | ==0.21.1 | production |
| prometheus-client | >=0.16.0 | test-legacy |
| structlog | ==25.1.0 | production, locked, environment |
| structlog | ==25.4.0 | full |
| structlog | >=23.0.0 | test-legacy |
| python-dateutil | ==2.9.0.post0 | production, locked, full, environment |
| python-dateutil | >=2.8.0 | test-legacy |
| pytz | ==2024.2 | production, locked, environment |
| pytz | ==2025.2 | full |
| pytz | >=2023.3 | test-legacy |
| mlflow | ==2.18.0 | production, locked, environment |
| mlflow | ==3.4.0 | full |
| mlflow | >=2.5.0 | test-legacy |
| scikit-learn | ==1.6.0 | production, locked, environment |
| scikit-learn | ==1.7.1 | full |
| scikit-learn | >=1.2.0 | test-legacy |
| joblib | ==1.4.2 | production, locked, environment |
| joblib | ==1.5.2 | full |
| typer | ==0.15.1 | production, locked, environment |
| typer | ==0.17.4 | full |
| rich | ==13.9.4 | production, locked, environment |
| rich | ==13.5.3 | full |
| pytest | ==8.3.4 | development, test, locked, environment |
| pytest | ==8.4.2 | full |
| pytest | >=7.0.0 | test-legacy |
| pytest | >=8.3.4 | setup.py-dev |
| pytest-asyncio | ==0.25.0 | development, test, locked, environment |
| pytest-asyncio | ==1.1.0 | full |
| pytest-asyncio | >=0.21.0 | test-legacy |
| pytest-asyncio | >=0.25.0 | setup.py-dev |
| pytest-cov | ==6.0.0 | development, test, locked, environment |
| pytest-cov | ==4.1.0 | full |
| pytest-cov | >=4.0.0 | test-legacy |
| pytest-cov | >=6.0.0 | setup.py-dev |
| pytest-mock | ==3.14.0 | development, test, locked, full, environment |
| pytest-mock | >=3.10.0 | test-legacy |
| pytest-mock | >=3.14.0 | setup.py-dev |
| pytest-xdist | ==3.6.1 | development, locked, environment |
| pytest-xdist | ==3.6.1  # 并行测试 | test |
| pytest-xdist | ==3.5.0 | full |
| pytest-xdist | >=3.0.0 | test-legacy |
| black | ==24.10.0 | development |
| black | ==25.9.0 | full |
| black | >=23.0.0 | test-legacy |
| black | >=24.10.0 | setup.py-dev |
| isort | ==5.13.2 | development, full |
| isort | >=5.12.0 | test-legacy |
| isort | >=5.13.2 | setup.py-dev |
| flake8 | ==7.1.1 | development |
| flake8 | ==7.3.0 | full |
| flake8 | >=6.0.0 | test-legacy |
| flake8 | >=7.1.1 | setup.py-dev |
| mypy | ==1.14.1 | development |
| mypy | ==1.18.2 | locked, environment |
| mypy | ==1.8.0 | full |
| mypy | >=1.4.0 | test-legacy |
| mypy | >=1.14.1 | setup.py-dev |
| ruff | ==0.8.4 | development |
| ruff | ==0.12.10 | full |
| pre-commit | ==4.0.1 | development |
| pre-commit | ==3.6.0 | full |
| ipython | ==8.31.0 | development |
| ipython | ==8.12.3 | full |
| ipython | >=8.0.0 | test-legacy |
| notebook | ==7.3.2 | development |
| notebook | ==7.4.5 | full |
| py-spy | ==0.3.14 | development |
| py-spy | >=0.3.0 | test-legacy |
| memory-profiler | ==0.61.0 | development, full |
| memory-profiler | >=0.61.0 | test-legacy |
| bandit | ==1.8.3 | development |
| bandit | ==1.8.6 | full |
| bandit | >=1.7.0 | test-legacy |
| safety | ==3.2.11 | development |
| safety | ==3.6.2 | full |
| safety | >=2.3.0 | test-legacy |
| types-redis | ==4.6.0.20250104 | development |
| types-redis | ==4.6.0.20241004 | full |
| types-requests | ==2.32.0.20250106 | development |
| types-requests | ==2.32.0.20240712 | full |
| types-python-dateutil | ==2.9.0.20250304 | development |
| types-python-dateutil | ==2.9.0.20250809 | full |
| python-dotenv | ==1.0.1 | development |
| python-dotenv | ==1.1.1 | locked, full, environment |
| python-dotenv | >=1.0.0 | test-legacy |
| factory-boy | ==3.3.1 | test |
| factory-boy | ==3.3.0 | full |
| faker | ==30.8.1 | test, locked, environment |
| faker | ==37.6.0 | full |
| responses | ==0.25.3 | test, locked, environment |
| responses | ==0.25.8 | full |
| locust | ==2.29.0 | test, locked, environment |
| locust | ==2.38.1 | full |
| anyio | ==4.11.0 | locked, environment |
| anyio | ==4.10.0 | full |
| bcrypt | ==5.0.0 | locked, environment |
| bcrypt | ==4.3.0 | full |
| bigtree | ==1.0.0 | locked, environment |
| bigtree | ==0.31.0 | full |
| billiard | ==4.2.2 | locked, environment |
| billiard | ==4.2.1 | full |
| coverage | ==7.10.7 | locked, environment |
| coverage | ==7.10.6 | full |
| dask | ==2025.9.1 | locked, environment |
| dask | ==2025.9.0 | full |
| databricks-sdk | ==0.67.0 | locked, environment |
| databricks-sdk | ==0.65.0 | full |
| dnspython | ==2.8.0 | locked, environment |
| dnspython | ==2.7.0 | full |
| docker | ==7.1.0 | locked, environment |
| docker | ==6.1.3 | full |
| feast | ==0.54.0 | locked, environment |
| feast | ==0.53.0 | full |
| flask | ==3.1.2 | locked, environment |
| flask | ==3.0.2 | full |
| fonttools | ==4.60.1 | locked, environment |
| fonttools | ==4.59.2 | full |
| fsspec | ==2025.9.0 | locked, environment |
| fsspec | ==2025.7.0 | full |
| gevent | ==25.9.1 | locked, environment |
| gevent | ==25.5.1 | full |
| google-auth | ==2.41.1 | locked, environment |
| google-auth | ==2.40.3 | full |
| importlib_metadata | ==8.7.0 | locked, environment |
| importlib_metadata | ==7.2.1 | full |
| jsonschema | ==4.25.1 | locked, environment |
| jsonschema | ==4.20.0 | full |
| jsonschema-specifications | ==2025.9.1 | locked, environment |
| jsonschema-specifications | ==2025.4.1 | full |
| markdown | ==3.9 | locked, environment |
| markdown | ==3.8.2 | full |
| markdown-it-py | ==4.0.0 | locked, environment |
| markdown-it-py | ==3.0.0 | full |
| markupsafe | ==3.0.3 | locked, environment |
| markupsafe | ==3.0.2 | full |
| matplotlib | ==3.10.6 | locked, environment |
| matplotlib | ==3.10.0 | full |
| mlflow-skinny | ==2.18.0 | locked, environment |
| mlflow-skinny | ==3.4.0 | full |
| packaging | ==24.2 | locked, environment |
| packaging | ==23.2 | full |
| prometheus_client | ==0.21.1 | locked, environment |
| prometheus_client | ==0.22.1 | full |
| prompt_toolkit | ==3.0.52 | locked, environment |
| prompt_toolkit | ==3.0.51 | full |
| protobuf | ==5.29.5 | locked, environment |
| protobuf | ==6.32.0 | full |
| psutil | ==7.1.0 | locked, environment |
| psutil | ==6.1.1 | full |
| psycopg | ==3.2.10 | locked, environment |
| psycopg | ==3.2.5 | full |
| pycparser | ==2.23 | locked, environment |
| pycparser | ==2.22 | full |
| pydantic_core | ==2.27.2 | locked, environment |
| pydantic_core | ==2.33.2 | full |
| pyparsing | ==3.2.5 | locked, environment |
| pyparsing | ==3.2.3 | full |
| pyyaml | ==6.0.3 | locked, full, environment |
| pyyaml | >=6.0.0 | test-legacy |
| pyzmq | ==27.1.0 | locked, environment |
| pyzmq | ==27.0.1 | full |
| rpds-py | ==0.27.1 | locked, environment |
| rpds-py | ==0.27.0 | full |
| scipy | ==1.16.2 | locked, environment |
| scipy | ==1.14.1 | full |
| starlette | ==0.41.3 | locked, environment |
| starlette | ==0.47.3 | full |
| tqdm | ==4.67.1 | locked, full, environment |
| tqdm | >=4.65.0 | test-legacy |
| typing_extensions | ==4.15.0 | locked, environment |
| typing_extensions | ==4.14.1 | full |
| urllib3 | ==2.5.0 | locked, environment |
| urllib3 | ==1.26.20 | full |
| wcwidth | ==0.2.14 | locked, environment |
| wcwidth | ==0.2.13 | full |
| werkzeug | ==3.1.3 | locked, environment |
| werkzeug | ==3.1.1 | full |
| zope.event | ==6.0 | locked, environment |
| zope.event | ==5.1.1 | full |
| zope.interface | ==8.0.1 | locked, environment |
| zope.interface | ==7.2 | full |
| aiosqlite | ==0.21.0 | full |
| aiosqlite | >=0.19.0 | test-legacy |
| ipdb | ==0.13.13 | full |
| ipdb | >=0.13.0 | test-legacy |
| marshmallow | ==3.26.1 | full |
| marshmallow | >=3.19.0 | test-legacy |
| openlineage-python | ==1.37.0 | full |
| openlineage-python | >=0.29.0 | test-legacy |
| pytest-postgresql | ==7.0.2 | full |
| pytest-postgresql | >=4.1.0 | test-legacy |
| python-json-logger | ==2.0.7 | full |
| python-json-logger | >=2.0.0 | test-legacy |
| sphinx | ==7.1.2 | full |
| sphinx | >=7.0.0 | test-legacy |
| sphinx-rtd-theme | ==1.3.0 | full |
| sphinx-rtd-theme | >=1.3.0 | test-legacy |

### 发现的问题


#### not_installed
Found 373 declared packages but not installed
```
adal, aiculture-kit, aiodns, aiofiles, aiomultiprocess, aiosqlite, alabaster, altair, apprise, apscheduler, argcomplete, argon2-cffi, argon2-cffi-bindings, arrow, asgi-lifespan, asteval, astroid, asttokens, async-lru, authlib, autoflake, autopep8, babel, backcall, backoff, backports.tempfile, backports.weakref, bandit, bc-detect-secrets, bc-jsonpath-ng, bc-python-hcl2, beartype, beautifulsoup4, bidict, binaryornot, black, bleach, boltons, boolean.py, boto3, botocore, bracex, build, cachecontrol, cached-property, cerberus, cfgv, chardet, checkov, click-option-group, cloudsplaining, colorlog, comm, confluent-kafka, contextlib2, cookiecutter, coolname, croniter, cyclonedx-python-lib, cyclopts, dateparser, debugpy, decorator, defusedxml, deprecated, detect-secrets, diff_cover, distlib, distro, dockerfile-parse, docopt, docstring_parser, docutils, dparse, dpath, email-validator, entrypoints, environs, et_xmlfile, exceptiongroup, executing, face, factory-boy, fakeredis, fancycompleter, fastapi-cli, fastjsonschema, fastmcp, filelock, flake8, flask-limiter, flask-talisman, football-predict-system, football-prediction, football-predictor, footballprediction, fqdn, glom, google-api-core, google-cloud-core, google-cloud-storage, google-crc32c, google-resumable-media, googleapis-common-protos, graphviz, great_expectations, griffe, h2, hiredis, holidays, hpack, html5lib, httpx-sse, humanfriendly, humanize, hyperframe, identify, imagesize, importlib_resources, ipdb, ipykernel, ipython, ipywidgets, isodate, isoduration, isort, jedi, jeepney, jinja2-humanize-extension, jiter, jmespath, json5, jsonpatch, jsonpickle, jsonpointer, jsonschema-path, junit-xml, jupyter, jupyter-console, jupyter-events, jupyter-lsp, jupyter_client, jupyter_core, jupyter_server, jupyter_server_terminals, jupyterlab, jupyterlab_pygments, jupyterlab_server, jupyterlab_widgets, kubernetes, lark, lazy-object-proxy, libcst, license-expression, limits, linkify-it-py, locust-cloud, lxml, mando, marshmallow, matplotlib-inline, mccabe, mcp, mdit-py-plugins, memory-profiler, mirakuru, mistune, mkdocs, mkdocs-material, mlflow-tracing, more-itertools, mplcursors, msal, msal-extensions, mutmut, nbclient, nbconvert, nbformat, ndg-httpsclient, nest-asyncio, networkx, nltk, nodeenv, notebook, notebook_shim, nvidia-nccl-cu12, oauthlib, openai, openapi-core, openapi-pydantic, openapi-schema-validator, openapi-spec-validator, openlineage-python, openlineage_sql, openpyxl, opentelemetry-exporter-otlp-proto-common, opentelemetry-exporter-otlp-proto-http, opentelemetry-instrumentation, opentelemetry-instrumentation-requests, opentelemetry-proto, opentelemetry-util-http, ordered-set, orjson, overrides, packageurl-python, pandocfilters, paramiko, parse, parso, pathable, pbr, pdbpp, peewee, pendulum, pep517, pexpect, pickleshare, pip, pip-api, pip-requirements-parser, pip-tools, pip_audit, pipdeptree, pipreqs, pkginfo, platformdirs, plette, ply, policy_sentry, port-for, posthog, pre-commit, prefect, prettytable, prometheus-client, prometheus-fastapi-instrumentator, prometheus_flask_exporter, proto-plus, psycopg-binary, ptyprocess, pure_eval, py-serializable, py-spy, pycares, pycep-parser, pycodestyle, pydantic-extra-types, pyflakes, pygame, pylint, pynacl, pyopenssl, pyperclip, pyproject-api, pyproject_hooks, pyqt5, pyqt5-qt5, pyqt5_sip, pyrepl, pysftp, pysocks, pyspnego, pytest-docker, pytest-postgresql, pytest-redis, pytest-testinfra, pytest-timeout, python-engineio, python-json-logger, python-slugify, python-socketio, python-socks, pytokens, pytzdata, pywinrm, radon, rdflib, readchar, regex, requests-auth-aws-sigv4, requests-mock, requests-oauthlib, requests_ntlm, requirementslib, rfc3339-validator, rfc3986-validator, rfc3987-syntax, rich-rst, rich-toolkit, ruamel.yaml, ruamel.yaml.clib, ruff, rustworkx, s3transfer, safety, safety-schemas, schedule, schema, seaborn, secretstorage, semantic-version, semgrep, semver, send2trash, setproctitle, setuptools, shellcheck_py, simple-websocket, slowapi, snowballstemmer, soupsieve, spdx-tools, sphinx, sphinx-rtd-theme, sphinxcontrib-applehelp, sphinxcontrib-devhelp, sphinxcontrib-htmlhelp, sphinxcontrib-jquery, sphinxcontrib-jsmath, sphinxcontrib-qthelp, sphinxcontrib-serializinghtml, sqlalchemy-utils, sse-starlette, stack-data, stevedore, termcolor, terminado, text-unidecode, textual, tinycss2, tomli, tomlkit, tornado, tox, traitlets, types-cachetools, types-cffi, types-croniter, types-jsonschema, types-psutil, types-psycopg2, types-pyopenssl, types-python-dateutil, types-pytz, types-pyyaml, types-redis, types-requests, types-setuptools, types-urllib3, typing-inspection, tzlocal, uc-micro-py, ujson, unidiff, uri-template, uritools, uv, virtualenv, watchdog, wcmatch, webcolors, webencodings, websocket-client, wheel, widgetsnbextension, wrapt, wsproto, xgboost, xlrd, xmltodict, xtquant, yamllint, yarg
```

#### duplicate_definitions
Found 199 packages defined in multiple files

## 🧩 环境差异说明

- **当前环境已安装**: 177 个包
- **已声明依赖**: 550 个包
- **已声明但未安装**: 373 个包

## 💡 优化建议

### 立即行动项
1. **使用 pip-tools**
   - 创建 `requirements.in` 文件定义直接依赖
   - 使用 `pip-compile` 生成锁定文件
   - 确保版本一致性

2. **清理依赖定义**
   - 统一使用 requirements.txt 系列文件
   - 移除 setup.py 中的重复定义
   - 使用 `-r` 引用避免重复

3. **版本管理改进**
   - 为所有包指定精确版本
   - 使用 `>=` 替代 `==` 以允许补丁更新
   - 定期更新依赖版本


## 📌 下一步行动建议

1. **短期** (1-2天)
   - [ ] 运行 `pip install pip-tools`
   - [ ] 创建 `requirements.in` 和 `requirements-dev.in`
   - [ ] 生成锁定文件 `pip-compile requirements.in`
   - [ ] 更新 CI/CD 使用锁定文件

2. **中期** (1周)
   - [ ] 实施依赖扫描自动化
   - [ ] 集成 Dependabot 或 Renovate
   - [ ] 建立依赖更新流程

3. **长期** (持续)
   - [ ] 定期审计依赖安全性
   - [ ] 监控依赖许可证变更
   - [ ] 评估并移除未使用的依赖


---

### 总结

⚠️ 发现 **99** 个版本冲突需要解决
⚠️ 发现 **572** 个依赖问题需要关注

建议立即实施 pip-tools 方案，实现更可靠的依赖管理。