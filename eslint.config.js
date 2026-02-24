/**
 * ESLint 配置 - V171-Standard-03
 *
 * 使用 ESLint 9.x flat config 格式
 */

module.exports = [
    {
        ignores: [
            'node_modules/**',
            'logs/**',
            'dist/**',
            '*.min.js',
        ],
    },
    {
        files: ['**/*.js'],
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: 'module',
            globals: {
                console: 'readonly',
                process: 'readonly',
                __dirname: 'readonly',
                __filename: 'readonly',
                Buffer: 'readonly',
                URL: 'readonly',
            },
        },
        rules: {
            'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
            'no-console': 'off',
            'prefer-const': 'warn',
            'no-var': 'error',
            'eqeqeq': ['error', 'always'],
            'curly': ['error', 'multi-line'],
            'no-throw-literal': 'error',
            'require-await': 'warn',
        },
    },
];
