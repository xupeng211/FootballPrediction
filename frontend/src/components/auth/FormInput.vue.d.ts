interface Props {
    name: string;
    label?: string;
    type?: string;
    placeholder?: string;
    modelValue: string | number;
    required?: boolean;
    disabled?: boolean;
    error?: string;
    hint?: string;
    autocomplete?: string;
    validateOnBlur?: boolean;
    validation?: (value: string) => string | null;
}
declare const _default: import("vue").DefineComponent<Props, {
    focus: () => void;
    blur: () => void;
}, {}, {}, {}, import("vue").ComponentOptionsMixin, import("vue").ComponentOptionsMixin, {} & {
    blur: (value: string) => any;
    "update:modelValue": (value: string) => any;
}, string, import("vue").PublicProps, Readonly<Props> & Readonly<{
    onBlur?: ((value: string) => any) | undefined;
    "onUpdate:modelValue"?: ((value: string) => any) | undefined;
}>, {
    type: string;
    required: boolean;
    disabled: boolean;
    autocomplete: string;
    validateOnBlur: boolean;
}, {}, {}, {}, string, import("vue").ComponentProvideOptions, false, {}, any>;
export default _default;
