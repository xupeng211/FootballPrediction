# 依赖与安全问题摘要

- `pip check`: 未发现依赖冲突
- 依赖安装：`requirements.lock`/`requirements.txt`/`requirements-dev.txt` 均成功安装（downgrade: mypy→1.8.0, uvicorn→0.24.0）
- `safety check --full-report`: 16 个漏洞（feast 0.47.0, knack 0.12.0 等）；详见原始报告



[33m[1m+===========================================================================================================================================================================================+[0m


[31m[1mDEPRECATED: [0m[33m[1mthis command (`check`) has been DEPRECATED, and will be unsupported beyond 01 June 2024.[0m


[32mWe highly encourage switching to the new [0m[32m[1m`scan`[0m[32m command which is easier to use, more powerful, and can be set up to mimic the deprecated command if required.[0m


[33m[1m+===========================================================================================================================================================================================+[0m


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

 [1mREPORT[0m 

  Safety [1mv3.6.1[0m is scanning for [1mVulnerabilities[0m[1m...[0m
[1m  Scanning dependencies[0m in your [1menvironment:[0m

  -> /home/user/.pyenv/versions/3.11.9/lib/python3.11/lib-dynload
  -> /home/user/projects/FootballPrediction/venv/lib/python3.11/site-packages
  -> /home/user/projects/FootballPrediction/venv/lib/python3.11/site-
  packages/_pdbpp_path_hack
  -> /home/user/.pyenv/versions/3.11.9/lib/python3.11
  -> /home/user/.pyenv/versions/3.11.9/lib/python311.zip
  -> /home/user/projects/FootballPrediction/venv/bin
  -> /home/user/projects/FootballPrediction/src
  -> /home/user/projects/FootballPrediction/venv/lib/python3.11/site-
  packages/setuptools/_vendor

  Using [1mopen-source vulnerability database[0m
[1m  Found and scanned 351 packages[0m
  Timestamp [1m2025-09-29 21:13:49[0m
[1m  16[0m[1m vulnerabilities reported[0m
[1m  0[0m[1m vulnerabilities ignored[0m

+==============================================================================+
 [1mVULNERABILITIES REPORTED[0m 
+==============================================================================+

[31m-> Vulnerability found in sqlalchemy-utils version 0.42.0[0m
[1m   Vulnerability ID: [0m42194
[1m   Affected spec: [0m>=0.27.0
[1m   ADVISORY: [0mSqlalchemy-utils from version 0.27.0 'EncryptedType'
   uses by default AES with CBC mode. The IV that it uses is not random
   though.https://github.com/kvesteri/sqlalchemy-
   utils/issues/166https://github.com/kvesteri/sqlalchemy-utils/pull/499
[1m   PVE-2021-42194[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/42194/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 42194 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in protobuf version 5.29.2[0m
[1m   Vulnerability ID: [0m77740
[1m   Affected spec: [0m>=5.26.0rc1,<5.29.5
[1m   ADVISORY: [0mAffected versions of this package are vulnerable to a
   potential Denial of Service (DoS) attack due to unbounded recursion when
   parsing untrusted Protocol Buffers data. The pure-Python implementation
   fails to enforce recursion depth limits when processing recursive groups,
   recursive messages, or a series of SGROUP tags, leading to stack overflow
   conditions that can crash the application by exceeding Python's recursion
   limit.
[1m   CVE-2025-4565[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/77740/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 77740 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in mlflow version 2.18.0[0m
[1m   Vulnerability ID: [0m78831
[1m   Affected spec: [0m>=2.17.0rc0,<2.20.3
[1m   ADVISORY: [0mAffected versions of the MLflow package are vulnerable
   to Cross-Site Request Forgery (CSRF) due to missing anti-CSRF token
   validation in the account creation functionality. The Signup feature in
   MLflow versions 2.17.0 to 2.20.1 fails to implement proper CSRF protection
   mechanisms, allowing unauthorized account creation requests to be
   processed without validating the request origin. An attacker can exploit
   this vulnerability by crafting a malicious webpage that submits a forged
   signup request to the MLflow server when visited by a victim, resulting in
   the creation of unauthorized user accounts that could be used to access
   the MLflow instance and perform malicious actions.
[1m   CVE-2025-1473[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/78831/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 78831 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in mlflow version 2.18.0[0m
[1m   Vulnerability ID: [0m71579
[1m   Affected spec: [0m>=1.27.0
[1m   ADVISORY: [0mDeserialization of untrusted data can occur in versions
   of the MLflow platform running version 1.27.0 or newer, enabling a
   maliciously crafted Recipe to execute arbitrary code on an end user’s
   system when run.
[1m   CVE-2024-37060[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/71579/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 71579 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in mlflow version 2.18.0[0m
[1m   Vulnerability ID: [0m71691
[1m   Affected spec: [0m>=0.5.0
[1m   ADVISORY: [0mDeserialization of untrusted data can occur in affected
   versions of the MLflow platform running, enabling a maliciously uploaded
   PyTorch model to run arbitrary code on an end user’s system when
   interacted with.
[1m   CVE-2024-37059[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/71691/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 71691 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in mlflow version 2.18.0[0m
[1m   Vulnerability ID: [0m71587
[1m   Affected spec: [0m>=0.9.0
[1m   ADVISORY: [0mDeserialization of untrusted data can occur in affected
   versions of the MLflow platform, enabling a maliciously uploaded PyFunc
   model to run arbitrary code on an end user’s system when interacted with.
[1m   CVE-2024-37054[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/71587/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 71587 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in mlflow version 2.18.0[0m
[1m   Vulnerability ID: [0m71692
[1m   Affected spec: [0m>=2.0.0rc0
[1m   ADVISORY: [0mDeserialization of untrusted data can occur in affected
   versions of the MLflow platform, enabling a maliciously uploaded
   Tensorflow model to run arbitrary code on an end user’s system when
   interacted with.
[1m   CVE-2024-37057[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/71692/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 71692 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in mlflow version 2.18.0[0m
[1m   Vulnerability ID: [0m71693
[1m   Affected spec: [0m>=1.24.0
[1m   ADVISORY: [0mDeserialization of untrusted data can occur in affected
   versions of the MLflow platform, enabling a maliciously uploaded pmdarima
   model to run arbitrary code on an end user’s system when interacted with.
[1m   CVE-2024-37055[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/71693/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 71693 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in mlflow version 2.18.0[0m
[1m   Vulnerability ID: [0m71578
[1m   Affected spec: [0m>=1.1.0
[1m   ADVISORY: [0mDeserialization of untrusted data can occur in versions
   of the MLflow platform running version 1.1.0 or newer, enabling a
   maliciously uploaded scikit-learn model to run arbitrary code on an end
   user’s system when interacted with.
[1m   CVE-2024-37053[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/71578/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 71578 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in mlflow version 2.18.0[0m
[1m   Vulnerability ID: [0m71577
[1m   Affected spec: [0m>=1.1.0
[1m   ADVISORY: [0mDeserialization of untrusted data can occur in versions
   of the MLflow platform running version 1.1.0 or newer, enabling a
   maliciously uploaded scikit-learn model to run arbitrary code on an end
   user’s system when interacted with.
[1m   CVE-2024-37052[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/71577/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 71577 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in mlflow version 2.18.0[0m
[1m   Vulnerability ID: [0m71584
[1m   Affected spec: [0m>=1.23.0
[1m   ADVISORY: [0mDeserialization of untrusted data can occur in versions
   of the MLflow platform affected versions, enabling a maliciously uploaded
   LightGBM scikit-learn model to run arbitrary code on an end user’s system
   when interacted with.
[1m   CVE-2024-37056[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/71584/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 71584 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in mlflow version 2.18.0[0m
[1m   Vulnerability ID: [0m77891
[1m   Affected spec: [0m< 3.1.0
[1m   ADVISORY: [0mAffected versions of this package are vulnerable to
   Server-Side Request Forgery (SSRF) due to insufficient validation of the
   gateway_path parameter in the gateway_proxy_handler function. The
   gateway_proxy_handler fails to properly validate the gateway_path
   parameter before proxying requests, leading to potential SSRF attacks
   where attackers can make the server perform unintended HTTP requests to
   internal or external resources.
[1m   CVE-2025-52967[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/77891/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 77891 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in mlflow version 2.18.0[0m
[1m   Vulnerability ID: [0m76179
[1m   Affected spec: [0m<2.19.0
[1m   ADVISORY: [0mIn mlflow/mlflow version 2.18, an admin is able to
   create a new user account without setting a password. This vulnerability
   could lead to security risks, as accounts without passwords may be
   susceptible to unauthorized access. Additionally, this issue violates best
   practices for secure user account management. The issue is fixed in
   version 2.19.0.
[1m   CVE-2025-1474[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/76179/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 76179 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in knack version 0.12.0[0m
[1m   Vulnerability ID: [0m79023
[1m   Affected spec: [0m<=0.12.0
[1m   ADVISORY: [0mAffected versions of the Microsoft Knack package are
   vulnerable to Regular Expression Denial of Service (ReDoS) attacks due to
   unbounded regular expression complexity. The `knack.introspection` module
   contains a regular expression pattern that exhibits exponential
   backtracking behaviour when processing specially crafted input strings.
[1m   CVE-2025-54363[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/79023/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 79023 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in knack version 0.12.0[0m
[1m   Vulnerability ID: [0m79027
[1m   Affected spec: [0m<=0.12.0
[1m   ADVISORY: [0mAffected versions of the Microsoft Knack package are
   vulnerable to Regular Expression Denial of Service (ReDoS) attacks due to
   catastrophic backtracking in a regular expression pattern. The
   `knack.introspection` module contains a regular expression with nested
   quantifiers that exhibits exponential time complexity when processing
   crafted input strings containing repetitive character sequences.
[1m   CVE-2025-54364[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/79027/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 79027 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


[31m-> Vulnerability found in feast version 0.47.0[0m
[1m   Vulnerability ID: [0m73884
[1m   Affected spec: [0m>0
[1m   ADVISORY: [0mFeast is potentially vulnerable to XSS in Jinja2
   Environment().
[1m   PVE-2024-73884[0m
[1m   For more information about this vulnerability, visit
   [0mhttps://data.safetycli.com/v/73884/97c[0m
   To ignore this vulnerability, use PyUp vulnerability id 73884 in safety’s
   ignore command-line argument or add the ignore to your safety policy file.


+==============================================================================+
   [32m[1mREMEDIATIONS[0m

  16 vulnerabilities were reported in 5 packages. For detailed remediation & 
  fix recommendations, upgrade to a commercial license. 

+==============================================================================+

 Scan was completed. 16 vulnerabilities were reported. 

+==============================================================================+[0m


[33m[1m+===========================================================================================================================================================================================+[0m


[31m[1mDEPRECATED: [0m[33m[1mthis command (`check`) has been DEPRECATED, and will be unsupported beyond 01 June 2024.[0m


[32mWe highly encourage switching to the new [0m[32m[1m`scan`[0m[32m command which is easier to use, more powerful, and can be set up to mimic the deprecated command if required.[0m


[33m[1m+===========================================================================================================================================================================================+[0m


