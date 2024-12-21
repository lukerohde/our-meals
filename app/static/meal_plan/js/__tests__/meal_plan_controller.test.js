import { Application } from '@hotwired/stimulus'
import MealPlanController from '../controllers/meal_plan_controller'

describe('MealPlanController', () => {
  let application

  beforeEach(() => {
    // Set up our document body
    document.body.innerHTML = `
      <div data-controller="meal-plan" 
           data-meal-plan-save-url-value="/save-grocery-list/"
           data-meal-plan-csrf-token-value="test-token">
        <textarea data-meal-plan-target="groceryList"></textarea>
        <span data-meal-plan-target="saveStatus"></span>
        <input type="text" data-meal-plan-target="shareLink" value="https://example.com/share" />
      </div>
    `

    // Start Stimulus application
    application = Application.start()
    application.register('meal-plan', MealPlanController)
  })

  afterEach(() => {
    // Clean up
    jest.useRealTimers()
  })

  describe('grocery list functionality', () => {
    beforeEach(() => {
      jest.useFakeTimers()
    })

    it('shows saving status when grocery list changes', () => {
      const textarea = document.querySelector('[data-meal-plan-target="groceryList"]')
      const status = document.querySelector('[data-meal-plan-target="saveStatus"]')

      textarea.value = 'New items'
      textarea.dispatchEvent(new Event('input'))

      expect(status.textContent).toBe('Saving...')
    })

    it('debounces save calls', () => {
      const textarea = document.querySelector('[data-meal-plan-target="groceryList"]')
      global.fetch = jest.fn()

      // Type multiple times
      textarea.value = 'Item 1'
      textarea.dispatchEvent(new Event('input'))

      textarea.value = 'Item 1, Item 2'
      textarea.dispatchEvent(new Event('input'))

      // Fast forward 1 second
      jest.advanceTimersByTime(1000)

      // Should not have called fetch yet
      expect(fetch).not.toHaveBeenCalled()

      // Fast forward remaining time
      jest.advanceTimersByTime(2000)

      // Should have called fetch once
      expect(fetch).toHaveBeenCalledTimes(1)
    })
  })

  describe('share link functionality', () => {
    it('copies link to clipboard', async () => {
      const mockClipboard = {
        writeText: jest.fn().mockResolvedValue(undefined),
      }
      Object.assign(navigator, {
        clipboard: mockClipboard,
      })

      const button = document.createElement('button')
      button.setAttribute('data-action', 'meal-plan#copyLink')
      document.body.appendChild(button)

      button.click()

      expect(mockClipboard.writeText).toHaveBeenCalledWith('https://example.com/share')
    })
  })
})
