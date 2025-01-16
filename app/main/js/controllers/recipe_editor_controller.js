import { Controller } from "@hotwired/stimulus"
import { showToast } from '../../../static/js/utils/toast'

export default class extends Controller {
  static targets = ["input", "submit", "loading"]

  connect() {
    console.log('RecipeEditor controller connected')
    // Set initial height
    this.autoExpand({ target: this.inputTarget })
    
    // Add tab key support for indentation
    this.inputTarget.addEventListener('keydown', this.handleTab.bind(this))
    
    // Add save shortcut handler
    document.addEventListener('keydown', this.handleSaveShortcut.bind(this))
  }

  disconnect() {
    this.inputTarget.removeEventListener('keydown', this.handleTab.bind(this))
    document.removeEventListener('keydown', this.handleSaveShortcut.bind(this))
  }

  handleSaveShortcut(event) {
    // Check for Cmd+S (Mac) or Ctrl+S (Windows/Linux)
    if ((event.metaKey || event.ctrlKey) && event.key === 's') {
      event.preventDefault()
      this.submitForm(new Event('submit'))
    }
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

  async submitForm(event) {
    event.preventDefault()

    // Show loading state
    this.submitTarget.classList.add('d-none')
    this.loadingTarget.classList.remove('d-none')

    try {
      const form = this.element
      const response = await fetch(form.action, {
        method: form.method,
        body: new FormData(form),
        headers: {
          'Accept': 'application/json',
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
      })

      const data = await response.json()
      
      if (response.ok) {
        if (data.redirect) {
          window.location.href = data.redirect
        } else {
          showToast('Changes saved successfully!', 'success')
        }
      } else {
        throw new Error(data.message || 'Failed to save changes')
      }
    } catch (error) {
      // Show error toast
      showToast(error.message, 'error')
      
      // Reset form state
      this.submitTarget.classList.remove('d-none')
      this.loadingTarget.classList.add('d-none')
    }
  }
}
