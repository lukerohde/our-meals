import '@testing-library/jest-dom'

// Mock Bootstrap Toast
global.bootstrap = {
  Toast: class {
    constructor() {}
    show() {}
  },
}
