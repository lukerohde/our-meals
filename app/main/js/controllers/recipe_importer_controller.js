import { Controller } from '@hotwired/stimulus'
import { showToast } from '../../../static/js/utils/toast'

export default class extends Controller {
  static targets = ['input', 'form', 'submit', 'loading']

  connect() {
    console.log('RecipeImporter controller connected')
  }

  submitForm(event) {
    event.preventDefault()
    const url = this.inputTarget.value.trim()

    if (!url || !this.isValidUrl(url)) {
      showToast('Please enter a valid recipe URL', 'warning')
      return
    }

    // Show loading state
    this.submitTarget.classList.add('d-none')
    this.loadingTarget.classList.remove('d-none')

    // Get the form data
    const formData = new FormData(this.formTarget)

    // Submit form via AJAX
    fetch(this.formTarget.action, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]').value
      },
      body: formData
    })
    .then(async response => {
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.message || 'Failed to import recipe')
      }
      return data
    })
    .then(data => {
      showToast('Recipe successfully imported!', 'success')
      window.location.href = data.redirect
    })
    .catch(error => {
      showToast(error.message || 'An error occurred while importing the recipe', 'error')
      this.resetFormState()
    })
  }

  resetFormState() {
    this.submitTarget.classList.remove('d-none')
    this.loadingTarget.classList.add('d-none')
  }

  isValidUrl(string) {
    try {
      new URL(string)
      return true
    } catch (_) {
      return false
    }
  }
}
