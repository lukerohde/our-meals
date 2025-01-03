import { Controller } from '@hotwired/stimulus'
import { showToast } from '../../../../static/js/utils/toast'

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

  // Helper method to animate and remove a card
  animateAndRemove(element) {
    const card = element.closest('.col')
    const height = card.offsetHeight
    
    // Set initial state
    card.style.cssText = `
      height: ${height}px;
      opacity: 1;
      margin-top: 0;
      overflow: hidden;
    `
    
    // Force a reflow
    card.offsetHeight
    
    // Add transitions
    card.style.transition = 'all 0.3s ease-out'
    
    // Trigger animation
    requestAnimationFrame(() => {
      card.style.height = '0'
      card.style.opacity = '0'
      card.style.marginTop = '-10px'
    })
    
    // Remove after animation
    setTimeout(() => card.remove(), 300)
  }

  delete(event) {
    event.preventDefault()
    
    if (!confirm(this.confirmMessageValue || 'Are you sure you want to delete this meal??')) {
      return
    }
    
    fetch(event.target.action, {
      method: 'POST',
      headers: {
        'HX-Request': 'true',
        'X-CSRFToken': event.target.querySelector('[name=csrfmiddlewaretoken]').value,
        'Accept': 'application/json',
      },
      body: new FormData(event.target)
    })
    .then(async response => {
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.message || 'Failed to delete meal')
      }
      return data
    })
    .then(data => {
      showToast(data.message, 'success')
      this.animateAndRemove(this.element)
    })
    .catch(error => {
      console.error('Error deleting meal:', error)
      showToast(error.message || 'Failed to delete meal', 'error')
    })
  }

  toggle(event) {
    event.preventDefault()
    
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
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.message || 'Failed to update meal plan')
      }
      return data
    })
    .then(data => {
      showToast(data.message, 'success')
      
      // If we're on the meal plan page and removing a meal, remove the card
      const onMealPlanPage = window.location.pathname.includes('/meal-plan/')
      const removingFromPlan = data.message.includes('removed from')
      
      if (onMealPlanPage && removingFromPlan) {
        this.animateAndRemove(this.element)
      } else {
        // Otherwise just update the toggle button state
        this.element.closest('.col').outerHTML = data.html
      }
    })
    .catch(error => {
      console.error('Error toggling meal:', error)
      showToast(error.message || 'Failed to update meal plan', 'error')
    })
  }
}
