import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import FormInput from '@/components/auth/FormInput.vue';
import LoadingButton from '@/components/auth/LoadingButton.vue';
const router = useRouter();
const authStore = useAuthStore();
const usernameInput = ref();
const confirmPasswordError = ref('');
const termsError = ref(false);
const form = reactive({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    agreeTerms: false
});
const validateUsername = (value) => {
    if (!value)
        return 'Username is required';
    if (value.length < 3)
        return 'Username must be at least 3 characters';
    if (value.length > 20)
        return 'Username must be less than 20 characters';
    if (!/^[a-zA-Z0-9_]+$/.test(value))
        return 'Username can only contain letters, numbers, and underscores';
    return null;
};
const validateEmail = (value) => {
    if (!value)
        return 'Email is required';
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value))
        return 'Please enter a valid email address';
    return null;
};
const validatePassword = (value) => {
    if (!value)
        return 'Password is required';
    if (value.length < 6)
        return 'Password must be at least 6 characters';
    // Check for stronger password requirements
    const hasUpperCase = /[A-Z]/.test(value);
    const hasLowerCase = /[a-z]/.test(value);
    const hasNumbers = /\d/.test(value);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(value);
    const strengthScore = [hasUpperCase, hasLowerCase, hasNumbers, hasSpecialChar].filter(Boolean).length;
    if (strengthScore < 3) {
        return 'Password should include uppercase, lowercase, numbers, and special characters';
    }
    return null;
};
const validateConfirmPassword = (value) => {
    if (!value)
        return 'Please confirm your password';
    if (value !== form.password)
        return 'Passwords do not match';
    return null;
};
const handleRegister = async () => {
    // Reset errors
    confirmPasswordError.value = '';
    termsError.value = false;
    // Validate all fields
    const usernameError = validateUsername(form.username);
    const emailError = validateEmail(form.email);
    const passwordError = validatePassword(form.password);
    const confirmError = validateConfirmPassword(form.confirmPassword);
    if (usernameError || emailError || passwordError || confirmError) {
        if (confirmError)
            confirmPasswordError.value = confirmError;
        return;
    }
    // Check terms agreement
    if (!form.agreeTerms) {
        termsError.value = true;
        return;
    }
    const success = await authStore.register({
        username: form.username,
        email: form.email,
        password: form.password,
        confirmPassword: form.confirmPassword
    });
    if (success) {
        router.push('/dashboard');
    }
};
// Focus on username input on mount
onMounted(() => {
    usernameInput.value?.focus();
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "max-w-md w-full space-y-8" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex justify-center" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex items-center" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "w-12 h-12 bg-primary-600 rounded-lg flex items-center justify-center" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.svg, __VLS_intrinsicElements.svg)({
    ...{ class: "h-8 w-8 text-white" },
    fill: "none",
    stroke: "currentColor",
    viewBox: "0 0 24 24",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.path)({
    'stroke-linecap': "round",
    'stroke-linejoin': "round",
    'stroke-width': "2",
    d: "M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({
    ...{ class: "mt-6 text-center text-3xl font-extrabold text-gray-900" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
    ...{ class: "mt-2 text-center text-sm text-gray-600" },
});
const __VLS_0 = {}.RouterLink;
/** @type {[typeof __VLS_components.RouterLink, typeof __VLS_components.routerLink, typeof __VLS_components.RouterLink, typeof __VLS_components.routerLink, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    to: "/login",
    ...{ class: "font-medium text-primary-600 hover:text-primary-500" },
}));
const __VLS_2 = __VLS_1({
    to: "/login",
    ...{ class: "font-medium text-primary-600 hover:text-primary-500" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_3.slots.default;
var __VLS_3;
__VLS_asFunctionalElement(__VLS_intrinsicElements.form, __VLS_intrinsicElements.form)({
    ...{ onSubmit: (__VLS_ctx.handleRegister) },
    ...{ class: "mt-8 space-y-6" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "space-y-4" },
});
/** @type {[typeof FormInput, ]} */ ;
// @ts-ignore
const __VLS_4 = __VLS_asFunctionalComponent(FormInput, new FormInput({
    ref: "usernameInput",
    name: "username",
    label: "Username",
    type: "text",
    placeholder: "Choose a username",
    modelValue: (__VLS_ctx.form.username),
    error: (__VLS_ctx.authStore.error?.field === 'username' ? __VLS_ctx.authStore.error?.message : null),
    required: true,
    autocomplete: "username",
    validation: (__VLS_ctx.validateUsername),
}));
const __VLS_5 = __VLS_4({
    ref: "usernameInput",
    name: "username",
    label: "Username",
    type: "text",
    placeholder: "Choose a username",
    modelValue: (__VLS_ctx.form.username),
    error: (__VLS_ctx.authStore.error?.field === 'username' ? __VLS_ctx.authStore.error?.message : null),
    required: true,
    autocomplete: "username",
    validation: (__VLS_ctx.validateUsername),
}, ...__VLS_functionalComponentArgsRest(__VLS_4));
/** @type {typeof __VLS_ctx.usernameInput} */ ;
var __VLS_7 = {};
var __VLS_6;
/** @type {[typeof FormInput, ]} */ ;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(FormInput, new FormInput({
    name: "email",
    label: "Email address",
    type: "email",
    placeholder: "Enter your email",
    modelValue: (__VLS_ctx.form.email),
    error: (__VLS_ctx.authStore.error?.field === 'email' ? __VLS_ctx.authStore.error?.message : null),
    required: true,
    autocomplete: "email",
    validation: (__VLS_ctx.validateEmail),
}));
const __VLS_10 = __VLS_9({
    name: "email",
    label: "Email address",
    type: "email",
    placeholder: "Enter your email",
    modelValue: (__VLS_ctx.form.email),
    error: (__VLS_ctx.authStore.error?.field === 'email' ? __VLS_ctx.authStore.error?.message : null),
    required: true,
    autocomplete: "email",
    validation: (__VLS_ctx.validateEmail),
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
/** @type {[typeof FormInput, ]} */ ;
// @ts-ignore
const __VLS_12 = __VLS_asFunctionalComponent(FormInput, new FormInput({
    name: "password",
    label: "Password",
    type: "password",
    placeholder: "Create a password",
    modelValue: (__VLS_ctx.form.password),
    error: (__VLS_ctx.authStore.error?.field === 'password' ? __VLS_ctx.authStore.error?.message : null),
    required: true,
    autocomplete: "new-password",
    validation: (__VLS_ctx.validatePassword),
    hint: "Must be at least 6 characters",
}));
const __VLS_13 = __VLS_12({
    name: "password",
    label: "Password",
    type: "password",
    placeholder: "Create a password",
    modelValue: (__VLS_ctx.form.password),
    error: (__VLS_ctx.authStore.error?.field === 'password' ? __VLS_ctx.authStore.error?.message : null),
    required: true,
    autocomplete: "new-password",
    validation: (__VLS_ctx.validatePassword),
    hint: "Must be at least 6 characters",
}, ...__VLS_functionalComponentArgsRest(__VLS_12));
/** @type {[typeof FormInput, ]} */ ;
// @ts-ignore
const __VLS_15 = __VLS_asFunctionalComponent(FormInput, new FormInput({
    name: "confirmPassword",
    label: "Confirm password",
    type: "password",
    placeholder: "Confirm your password",
    modelValue: (__VLS_ctx.form.confirmPassword),
    error: (__VLS_ctx.confirmPasswordError),
    required: true,
    autocomplete: "new-password",
    validation: (__VLS_ctx.validateConfirmPassword),
}));
const __VLS_16 = __VLS_15({
    name: "confirmPassword",
    label: "Confirm password",
    type: "password",
    placeholder: "Confirm your password",
    modelValue: (__VLS_ctx.form.confirmPassword),
    error: (__VLS_ctx.confirmPasswordError),
    required: true,
    autocomplete: "new-password",
    validation: (__VLS_ctx.validateConfirmPassword),
}, ...__VLS_functionalComponentArgsRest(__VLS_15));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex items-center" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.input)({
    id: "agree-terms",
    name: "agree-terms",
    type: "checkbox",
    ...{ class: "h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded" },
    ...{ class: ({ 'border-red-300': __VLS_ctx.termsError }) },
});
(__VLS_ctx.form.agreeTerms);
__VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({
    for: "agree-terms",
    ...{ class: "ml-2 block text-sm text-gray-900" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.a, __VLS_intrinsicElements.a)({
    href: "#",
    ...{ class: "text-primary-600 hover:text-primary-500" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.a, __VLS_intrinsicElements.a)({
    href: "#",
    ...{ class: "text-primary-600 hover:text-primary-500" },
});
if (__VLS_ctx.termsError) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "mt-1 text-sm text-red-600" },
    });
}
if (__VLS_ctx.authStore.error && !__VLS_ctx.authStore.error?.field) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "rounded-md bg-red-50 p-4" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex-shrink-0" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.svg, __VLS_intrinsicElements.svg)({
        ...{ class: "h-5 w-5 text-red-400" },
        viewBox: "0 0 20 20",
        fill: "currentColor",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.path)({
        'fill-rule': "evenodd",
        d: "M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z",
        'clip-rule': "evenodd",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "ml-3" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({
        ...{ class: "text-sm font-medium text-red-800" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "mt-2 text-sm text-red-700" },
    });
    (__VLS_ctx.authStore.error.message);
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
/** @type {[typeof LoadingButton, ]} */ ;
// @ts-ignore
const __VLS_18 = __VLS_asFunctionalComponent(LoadingButton, new LoadingButton({
    text: "Create account",
    loading: (__VLS_ctx.authStore.loading),
    loadingText: "Creating account...",
    type: "submit",
    variant: "primary",
    size: "md",
    fullWidth: true,
}));
const __VLS_19 = __VLS_18({
    text: "Create account",
    loading: (__VLS_ctx.authStore.loading),
    loadingText: "Creating account...",
    type: "submit",
    variant: "primary",
    size: "md",
    fullWidth: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_18));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
    ...{ class: "text-sm font-medium text-gray-900 mb-2" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.ul, __VLS_intrinsicElements.ul)({
    ...{ class: "text-xs text-gray-600 space-y-1" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({});
/** @type {__VLS_StyleScopedClasses['min-h-screen']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-gray-50']} */ ;
/** @type {__VLS_StyleScopedClasses['py-12']} */ ;
/** @type {__VLS_StyleScopedClasses['px-4']} */ ;
/** @type {__VLS_StyleScopedClasses['sm:px-6']} */ ;
/** @type {__VLS_StyleScopedClasses['lg:px-8']} */ ;
/** @type {__VLS_StyleScopedClasses['max-w-md']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['space-y-8']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['w-12']} */ ;
/** @type {__VLS_StyleScopedClasses['h-12']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-primary-600']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['h-8']} */ ;
/** @type {__VLS_StyleScopedClasses['w-8']} */ ;
/** @type {__VLS_StyleScopedClasses['text-white']} */ ;
/** @type {__VLS_StyleScopedClasses['mt-6']} */ ;
/** @type {__VLS_StyleScopedClasses['text-center']} */ ;
/** @type {__VLS_StyleScopedClasses['text-3xl']} */ ;
/** @type {__VLS_StyleScopedClasses['font-extrabold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-gray-900']} */ ;
/** @type {__VLS_StyleScopedClasses['mt-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-center']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-gray-600']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-600']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-primary-500']} */ ;
/** @type {__VLS_StyleScopedClasses['mt-8']} */ ;
/** @type {__VLS_StyleScopedClasses['space-y-6']} */ ;
/** @type {__VLS_StyleScopedClasses['space-y-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['h-4']} */ ;
/** @type {__VLS_StyleScopedClasses['w-4']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-600']} */ ;
/** @type {__VLS_StyleScopedClasses['focus:ring-primary-500']} */ ;
/** @type {__VLS_StyleScopedClasses['border-gray-300']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['ml-2']} */ ;
/** @type {__VLS_StyleScopedClasses['block']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-gray-900']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-600']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-primary-500']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary-600']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-primary-500']} */ ;
/** @type {__VLS_StyleScopedClasses['mt-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-red-600']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-md']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-red-50']} */ ;
/** @type {__VLS_StyleScopedClasses['p-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['h-5']} */ ;
/** @type {__VLS_StyleScopedClasses['w-5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-red-400']} */ ;
/** @type {__VLS_StyleScopedClasses['ml-3']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['text-red-800']} */ ;
/** @type {__VLS_StyleScopedClasses['mt-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['text-red-700']} */ ;
/** @type {__VLS_StyleScopedClasses['mt-6']} */ ;
/** @type {__VLS_StyleScopedClasses['p-4']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-gray-50']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['border-gray-200']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['text-gray-900']} */ ;
/** @type {__VLS_StyleScopedClasses['mb-2']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['text-gray-600']} */ ;
/** @type {__VLS_StyleScopedClasses['space-y-1']} */ ;
// @ts-ignore
var __VLS_8 = __VLS_7;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            FormInput: FormInput,
            LoadingButton: LoadingButton,
            authStore: authStore,
            usernameInput: usernameInput,
            confirmPasswordError: confirmPasswordError,
            termsError: termsError,
            form: form,
            validateUsername: validateUsername,
            validateEmail: validateEmail,
            validatePassword: validatePassword,
            validateConfirmPassword: validateConfirmPassword,
            handleRegister: handleRegister,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
