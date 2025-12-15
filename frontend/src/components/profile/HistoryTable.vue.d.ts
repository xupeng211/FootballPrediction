import { HistoryRecord } from '@/types/prediction';
interface Props {
    records: HistoryRecord[];
    loading?: boolean;
    hasMore?: boolean;
}
declare const _default: import("vue").DefineComponent<Props, {}, {}, {}, {}, import("vue").ComponentOptionsMixin, import("vue").ComponentOptionsMixin, {
    loadMore: () => any;
}, string, import("vue").PublicProps, Readonly<Props> & Readonly<{
    onLoadMore?: (() => any) | undefined;
}>, {
    loading: boolean;
    hasMore: boolean;
}, {}, {}, {}, string, import("vue").ComponentProvideOptions, false, {}, any>;
export default _default;
