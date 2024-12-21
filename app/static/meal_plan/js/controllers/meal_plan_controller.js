import { Controller } from '@hotwired/stimulus'

/**
 * Meal Plan Controller
 *
 * Handles the interactive features of the meal plan detail page:
 * - Auto-saving grocery list
 * - Copying share link
 * - Toast notifications
 */
export default class extends Controller {
  static targets = ['groceryList', 'saveStatus', 'shareLink']

  static values = {
    saveUrl: String,
    csrfToken: String,
  }

  connect() {
    console.log('MealPlanController connected')
    console.log('Targets available:', {
      groceryList: this.hasGroceryListTarget,
      saveStatus: this.hasSaveStatusTarget,
      shareLink: this.hasShareLinkTarget,
    })
    console.log('Values:', {
      saveUrl: this.saveUrlValue,
      csrfToken: this.csrfTokenValue,
    })

    if (this.hasGroceryListTarget) {
      this.setupAutoSave()
    }
  }

  /**
   * Sets up auto-save functionality for grocery list
   * Debounces save calls to prevent excessive server requests
   */
  setupAutoSave() {
    let saveTimeout
    this.groceryListTarget.addEventListener('input', () => {
      clearTimeout(saveTimeout)
      this.saveStatusTarget.textContent = 'Saving...'
      saveTimeout = setTimeout(() => this.saveGroceryList(), 1000) // 3 second debounce
    })
  }

  /**
   * Saves grocery list to server
   * Handles success/failure states and updates UI accordingly
   */
  async saveGroceryList() {
    const data = new FormData()
    data.append('grocery_list', this.groceryListTarget.value)

    try {
      const response = await fetch(this.saveUrlValue, {
        method: 'POST',
        headers: {
          'X-CSRFToken': this.csrfTokenValue,
        },
        body: data,
      })

      if (response.ok) {
        this.saveStatusTarget.textContent = 'Changes saved'
        setTimeout(() => {
          this.saveStatusTarget.textContent = ''
        }, 2000)
      } else {
        throw new Error('Server responded with error')
      }
    } catch (error) {
      this.saveStatusTarget.textContent = 'Error saving changes'
      console.error('Failed to save grocery list:', error)
    }
  }

  /**
   * Copies share link to clipboard
   * Shows success/failure toast notification
   */
  async copyLink() {
    try {
      await navigator.clipboard.writeText(this.shareLinkTarget.value)
      this.showToast('Link copied to clipboard!')
    } catch (err) {
      this.showToast('Failed to copy link', false)
      console.error('Failed to copy link:', err)
    }
  }

  /**
   * Shows a toast notification
   * @param {string} message - Message to display
   * @param {boolean} [success=true] - Whether this is a success message
   */
  showToast(message, success = true) {
    const toast = document.createElement('div')
    toast.className = 'position-fixed bottom-0 end-0 p-3'
    toast.style.zIndex = '11'
    toast.innerHTML = `
      <div class="toast align-items-center text-white bg-${success ? 'success' : 'danger'} border-0" 
           role="alert" aria-live="assertive" aria-atomic="true">
        <div class="d-flex">
          <div class="toast-body">
            <i class="bi bi-${success ? 'check-circle' : 'x-circle'} me-2"></i>${message}
          </div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                  data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
      </div>
    `
    document.body.appendChild(toast)
    const toastEl = new bootstrap.Toast(toast.querySelector('.toast'))
    toastEl.show()

    toast.addEventListener('hidden.bs.toast', () => {
      document.body.removeChild(toast)
    })
  }
}
