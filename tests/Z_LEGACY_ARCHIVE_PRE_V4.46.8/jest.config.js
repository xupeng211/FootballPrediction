{
  "testEnvironment": "node",
  "testMatch": [
    "**/tests/**/*.test.js"
  ],
  "collectCoverageFrom": [
    "src/**/*.js",
    "!src/**/node_modules/**",
    "!src/**/*.test.js"
  ],
  "coverageThreshold": {
    "global": {
      "branches": 70,
      "functions": 70,
      "lines": 70,
      "statements": 70
    },
    "./src/infrastructure/engines/parsers/TrajectoryParser.js": {
      "branches": 80,
      "functions": 80,
      "lines": 80,
      "statements": 80
    }
  },
  "coverageReporters": [
    "text",
    "lcov",
    "html"
  ],
  "verbose": true,
  "transformIgnorePatterns": [
    "node_modules/(?!(?:@exodus/bytes|html-encoding-sniffer)/)"
  ],
  "moduleNameMapper": {
    "^@/(.*)$": "<rootDir>/src/$1"
  },
  "testPathIgnorePatterns": [
    "/node_modules/",
    "/fixtures/"
  ]
}
