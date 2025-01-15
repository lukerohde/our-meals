import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["input"]

  connect() {
    // Set initial height
    this.autoExpand({ target: this.inputTarget })
    
    // Add tab key support for indentation
    this.inputTarget.addEventListener('keydown', this.handleTab.bind(this))
  }

  disconnect() {
    this.inputTarget.removeEventListener('keydown', this.handleTab.bind(this))
  }

  autoExpand(event) {
    const textarea = event.target
    // Reset height to ensure proper calculation
    textarea.style.height = 'auto'
    // Set new height based on content
    textarea.style.height = `${textarea.scrollHeight}px`
  }

  handleTab(event) {
    if (event.key === 'Tab') {
      event.preventDefault()
      
      const start = this.inputTarget.selectionStart
      const end = this.inputTarget.selectionEnd
      const value = this.inputTarget.value
      
      // Insert tab at cursor position
      this.inputTarget.value = value.substring(0, start) + '  ' + value.substring(end)
      
      // Move cursor after tab
      this.inputTarget.selectionStart = this.inputTarget.selectionEnd = start + 2
    }
  }
}
