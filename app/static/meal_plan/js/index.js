/**
 * Meal Plan Module Entry Point
 *
 * This module initializes the Stimulus application for the meal plan feature.
 * It keeps the meal plan functionality isolated from other parts of the application.
 */

import { Application } from '@hotwired/stimulus'
import MealPlanController from './controllers/meal_plan_controller'

let application = null

if (module.hot) {
  module.hot.accept() // tell hmr to accept updates

  if (module.hot.data) {
    application = module.hot.data.application // re-use old application if one was passed after update
  }

  module.hot.dispose((data) => {
    data.application = application // on disposal of the old version (before reload), pass the old application to the new version
  })
}

// Initialize the application if it doesn't exist
if (!application) {
  console.log('Initializing Meal Plan module...')
  try {
    application = Application.start()
    console.log('Meal Plan module initialized successfully')
  } catch (error) {
    console.error('Failed to initialize Meal Plan module:', error)
  }
}

// Register controllers
application.register('meal-plan', MealPlanController)
