interface Props {
    title?: string;
    message: string;
    showRetry?: boolean;
}
declare const _default: import("vue").DefineComponent<Props, {}, {}, {}, {}, import("vue").ComponentOptionsMixin, import("vue").ComponentOptionsMixin, {
    retry: () => any;
}, string, import("vue").PublicProps, Readonly<Props> & Readonly<{
    onRetry?: (() => any) | undefined;
}>, {
    title: string;
    showRetry: boolean;
}, {}, {}, {}, string, import("vue").ComponentProvideOptions, false, {}, any>;
export default _default;
