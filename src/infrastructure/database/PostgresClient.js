/**
 * V171-Standard-01 统一配置管理
 * ==============================
 *
 * 安全规范:
 * - 所有敏感信息通过 process.env 读取
 * - 严禁硬编码密码
 * - 提供默认值仅用于开发环境
 *
 * @module config/database
 */

'use strict';

const path = require('path');
const fs = require('fs');

// 加载 .env 文件
function loadEnvFile() {
    const envPath = path.resolve(__dirname, '../../.env');
    if (fs.existsSync(envPath)) {
        const content = fs.readFileSync(envPath, 'utf8');
        content.split('\n').forEach(line => {
            const trimmed = line.trim();
            if (trimmed && !trimmed.startsWith('#')) {
                const [key, ...values] = trimmed.split('=');
                if (key && values.length > 0 && !process.env[key]) {
                    process.env[key] = values.join('=').replace(/^["']|["']$/g, '');
                }
            }
        });
    }
}

// 尝试加载 .env
loadEnvFile();

/**
 * 数据库配置
 */
const DatabaseConfig = {
    get host() {
        return process.env.DB_HOST || 'localhost';
    },
    get port() {
        return parseInt(process.env.DB_PORT || '5432', 10);
    },
    get database() {
        return process.env.DB_NAME || 'football_db';
    },
    get user() {
        return process.env.DB_USER || 'football_user';
    },
    get password() {
        // V190: 生产环境必须设置 DB_PASSWORD
        const password = process.env.DB_PASSWORD;
        if (!password) {
            console.warn('⚠️ DB_PASSWORD 未设置，请在 .env 文件中配置');
            return '';  // 返回空字符串而非硬编码密码
        }
        return password;
    },
    get connectionString() {
        return `postgresql://${this.user}:${this.password}@${this.host}:${this.port}/${this.database}`;
    }
};

/**
 * 代理配置
 */
const ProxyConfig = {
    get enabled() {
        return process.env.ENABLE_PROXY_ROTATION === 'true';
    },
    get host() {
        return process.env.PROXY_HOST || '127.0.0.1';
    },
    get portStart() {
        return parseInt(process.env.PROXY_PORT_START || '7891', 10);
    },
    get portEnd() {
        return parseInt(process.env.PROXY_PORT_END || '7912', 10);
    },
    get protocol() {
        return process.env.PROXY_PROTOCOL || 'http';
    }
};

/**
 * 收割配置
 */
const HarvestConfig = {
    get concurrentThreads() {
        return parseInt(process.env.CONCURRENT_THREADS || '5', 10);
    },
    get headless() {
        return process.env.HEADLESS_MODE !== 'false';
    },
    get waitBaseMs() {
        return parseInt(process.env.WAIT_BASE_MS || '2000', 10);
    },
    get waitJitterMs() {
        return parseInt(process.env.WAIT_JITTER_MS || '1500', 10);
    }
};

/**
 * 日志配置
 */
const LogConfig = {
    get level() {
        return process.env.LOG_LEVEL || 'info';
    },
    get logDir() {
        return process.env.LOG_DIR || path.resolve(__dirname, '../../logs');
    }
};

/**
 * 验证配置完整性
 */
function validateConfig() {
    const errors = [];
    const warnings = [];

    // 检查必要的环境变量
    if (!process.env.DB_PASSWORD) {
        warnings.push('DB_PASSWORD 未设置');
    }

    if (process.env.NODE_ENV === 'production') {
        if (!process.env.DB_PASSWORD) {
            errors.push('生产环境必须设置 DB_PASSWORD');
        }
    }

    return { errors, warnings, valid: errors.length === 0 };
}

/**
 * 获取配置摘要 (不包含敏感信息)
 */
function getConfigSummary() {
    return {
        database: {
            host: DatabaseConfig.host,
            port: DatabaseConfig.port,
            database: DatabaseConfig.database,
            user: DatabaseConfig.user,
            passwordSet: !!process.env.DB_PASSWORD
        },
        proxy: {
            enabled: ProxyConfig.enabled,
            host: ProxyConfig.host,
            portRange: `${ProxyConfig.portStart}-${ProxyConfig.portEnd}`
        },
        harvest: {
            concurrentThreads: HarvestConfig.concurrentThreads,
            headless: HarvestConfig.headless
        },
        log: {
            level: LogConfig.level,
            logDir: LogConfig.logDir
        }
    };
}

module.exports = {
    DatabaseConfig,
    ProxyConfig,
    HarvestConfig,
    LogConfig,
    validateConfig,
    getConfigSummary
};
