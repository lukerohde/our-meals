import { Controller } from '@hotwired/stimulus'

export default class extends Controller {
  static targets = ['input']

  connect() {
    console.log('RecipeImporter controller connected')
  }

  submitForm(event) {
    const url = this.inputTarget.value.trim()
    console.log('Form submitted with URL:', url)

    if (!url || !this.isValidUrl(url)) {
      event.preventDefault()
      alert('Please enter a valid recipe URL')
      return false
    }
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
