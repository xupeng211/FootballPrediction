import { UserProfile } from '@/types/prediction';
interface Props {
    profile: UserProfile;
    historyStats?: {
        win_count: number;
        loss_count: number;
        push_count: number;
        total_bets: number;
    };
    showDetailed?: boolean;
}
declare const _default: import("vue").DefineComponent<Props, {}, {}, {}, {}, import("vue").ComponentOptionsMixin, import("vue").ComponentOptionsMixin, {}, string, import("vue").PublicProps, Readonly<Props> & Readonly<{}>, {
    showDetailed: boolean;
}, {}, {}, {}, string, import("vue").ComponentProvideOptions, false, {}, any>;
export default _default;
