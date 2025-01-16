import { Application } from '@hotwired/stimulus'
import MealPlanController from '../../main/js/controllers/meal_plan_controller'
import RecipeImporterController from '../../main/js/controllers/recipe_importer_controller'
import RecipeEditorController from '../../main/js/controllers/recipe_editor_controller'
import MealActionsController from '../../main/js/controllers/meal_actions_controller'

console.log('Loading Stimulus application...')

let application = null

if (module.hot) {
    module.hot.accept()

    if (module.hot.data) {
        application = module.hot.data.application
    }

    module.hot.dispose(data => {
        data.application = application
    })
}

if (!application) {
    console.log('Initializing application...')
    try {
        application = Application.start()
        console.log('Application initialized successfully')

        // Register all controllers
     } catch (error) {
        console.error('Failed to initialize application:', error)
    }
}

console.log('Registering controllers...')
application.register('meal-plan', MealPlanController)
application.register('recipe-importer', RecipeImporterController)
application.register('recipe-editor', RecipeEditorController)
application.register('meal-actions', MealActionsController)
console.log('Controllers registered successfully')


// Export the application instance for other modules to use
export { application }
