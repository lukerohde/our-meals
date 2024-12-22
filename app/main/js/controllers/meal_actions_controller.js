import { Controller } from '@hotwired/stimulus'

/**
 * Meal Actions Controller
 * 
 * Handles meal actions like adding to meal plan and deletion
 * with confirmation dialogs and loading states
 */
export default class extends Controller {
  static values = {
    confirmMessage: String
  }

  connect() {
    console.log('MealActions controller connected')
  }

  delete(event) {
    if (!confirm(this.confirmMessageValue || 'Are you sure?')) {
      event.preventDefault()
    }
  }

  // Placeholder for future AJAX toggle
  toggle(event) {
    console.log('Toggle meal in plan')
    // For now, just let the form submit normally
    // Later we can add AJAX here
  }
}
