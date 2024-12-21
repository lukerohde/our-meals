module.exports = {
  env: {
    browser: true,
    es2021: true,
    jest: true,
    node: true  // For module, require, etc.
  },
  extends: [
    'eslint:recommended',
    'prettier'
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module'
  },
  rules: {
    'no-console': ['warn', { allow: ['error', 'warn'] }],
    'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    'prefer-const': 'error',
    'no-var': 'error'
  },
  globals: {
    bootstrap: 'readonly',  // For Bootstrap Toast
    module: 'readonly'      // For HMR
  }
}
