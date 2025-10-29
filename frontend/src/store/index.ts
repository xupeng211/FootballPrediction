import { configureStore } from '@reduxjs/toolkit';
import matchesReducer from './slices/matchesSlice';
import predictionsReducer from './slices/predictionsSlice';
import uiReducer from './slices/uiSlice';

export const store = configureStore({
  reducer: {
    matches: matchesReducer,
    predictions: predictionsReducer,
    ui: uiReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export default store;