module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/static/meal_plan/js/__tests__/setup.js'],
  moduleDirectories: ['node_modules', '<rootDir>/static/meal_plan/js'],
  transform: {
    "^.+\\.js$": "babel-jest"
  },
  collectCoverage: true,
  collectCoverageFrom: [
    'static/meal_plan/js/**/*.js',
    '!static/meal_plan/js/__tests__/**'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  }
}
