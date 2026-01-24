/**
 * V43.300 PM2 Ecosystem Configuration
 * ====================================
 *
 * Production-ready process manager configuration for temporal sync engine
 *
 * Core Features:
 *   - Auto-restart on crash (1 second delay)
 *   - Memory limit: 1GB
 *   - Log persistence with rotation
 *   - Environment-specific configuration
 *   - Graceful shutdown on SIGINT/SIGTERM
 *
 * Usage:
 *   pm2 start ecosystem.config.js --env production
 *   pm2 save
 *   pm2 startup
 *
 * @author Lead Systems Reliability Engineer (SRE)
 * @version V43.300
 * @date 2026-01-24
 */

module.exports = {
  apps: [{
    name: 'temporal-sync-engine',

    // Script entry point
    script: './scripts/ops/temporal_sync_engine.js',

    // Interpreter
    interpreter: 'node',

    // Instances
    instances: 1,
    exec_mode: 'fork',

    // Auto-restart configuration
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    min_uptime: '10s',
    restart_delay: 1000,

    // Log configuration
    error_file: './logs/pm2_error.log',
    out_file: './logs/pm2_out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    merge_logs: true,

    // Environment variables
    env_production: {
      NODE_ENV: 'production',
      DEBUG: 'false'
    },

    env_development: {
      NODE_ENV: 'development',
      DEBUG: 'true'
    }
  }],

  // Deployment configuration
  deploy: {
    production: {
      user: 'NODE',
      host: 'localhost',
      ref: 'origin/main',
      repo: 'git@github.com:username/football-prediction.git',
      path: '/home/user/projects/FootballPrediction',
      'post-deploy': 'npm install --production && pm2 reload ecosystem.config.js --env production'
    }
  }
};
