import { Controller } from '@hotwired/stimulus'
import { showToast } from '../../../static/js/utils/toast'

/**
 * Meal Actions Controller
 * 
 * Handles meal actions like adding to meal plan and deletion
 * with confirmation dialogs and loading states
 */
export default class extends Controller {
  static targets = ['form']

  static values = {
    confirmMessage: String
  }

  connect() {
    console.log('MealActions controller connected')
  }

  delete(event) {
    if (!confirm(this.confirmMessageValue || 'Are you sure???')) {
      event.preventDefault()
    }
  }

  toggle(event) {
    event.preventDefault()
    
    try {
      fetch(this.formTarget.action, {
        method: 'POST',
        headers: {
          'HX-Request': 'true',
          'X-CSRFToken': this.formTarget.querySelector('[name=csrfmiddlewaretoken]').value,
          'Accept': 'application/json',
        },
        body: new FormData(this.formTarget)
      })
      .then(async response => {
        if (!response.ok) {
          const errorText = await response.text()
          showToast(errorText, 'error')
          return
        }
        
        const data = await response.json()
        // Replace the entire meal card with the new version
        this.element.closest('.col').outerHTML = data.html
        // Show the message from Django
        showToast(data.message, 'success')
      })
      
    } catch (error) {
      console.error('Error toggling meal:', error)
      showToast('Failed to update meal plan', 'error')
    }
  }
}
