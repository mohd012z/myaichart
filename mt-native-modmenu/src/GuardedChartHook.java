package mt.nativeaddon;

import android.app.Activity;
import android.os.Looper;
import android.view.View;
import android.widget.FrameLayout;

/**
 * Guardrail/Softrail for a caller-provided, verified chart view.
 * No offsets, private-view scanning, native patching or trade interception.
 */
public final class GuardedChartHook {
    public enum Result {
        ATTACHED, ALREADY_ATTACHED, SOFT_SKIPPED, BLOCKED
    }
    private final Activity activity;
    private final ChartViewHookBridge bridge;
    private View observed;
    private View.OnAttachStateChangeListener listener;
    private boolean enabled;
    private int attachedChartId = -1;
    private long attachedRevision = -1L;

    public GuardedChartHook(Activity activity, Mt5ResearchMenu.Listener callback) {
        if (activity == null || callback == null)
            throw new IllegalArgumentException("activity/callback");
        this.activity = activity;
        this.bridge = new ChartViewHookBridge(activity, callback);
    }

    /** Explicit opt-in, off by default. */
    public void setEnabled(boolean value) {
        mainThread();
        enabled = value;
        if (!value) detach();
    }

    /**
     * Guardrail: reject invalid identity and wrong-thread access.
     * Softrail: skip unsupported view parents and detached views.
     */
    public Result tryAttach(View chart, int chartId, long viewportRevision) {
        mainThread();
        if (!enabled || chart == null || chartId < 0 || viewportRevision < 0)
            return Result.BLOCKED;
        if (chart.getWindowToken() == null
                || !(chart.getParent() instanceof FrameLayout)
                || chart.getContext() != activity)
            return Result.SOFT_SKIPPED;
        if (observed == chart && bridge.isAttached()
                && attachedChartId == chartId && attachedRevision == viewportRevision)
            return Result.ALREADY_ATTACHED;
        detach();
        try {
            bridge.onChartAttached(chart, chartId, viewportRevision);
        } catch (IllegalArgumentException | IllegalStateException exception) {
            detach();
            return Result.SOFT_SKIPPED;
        }
        observed = chart;
        attachedChartId = chartId;
        attachedRevision = viewportRevision;
        listener = new View.OnAttachStateChangeListener() {
            @Override public void onViewAttachedToWindow(View view) { }
            @Override public void onViewDetachedFromWindow(View view) {
                if (view == observed) detach();
            }
        };
        chart.addOnAttachStateChangeListener(listener);
        return Result.ATTACHED;
    }

    public void onChartChanged(int chartId, long revision) {
        mainThread();
        bridge.onChartChanged(chartId, revision);
        if (!bridge.isAttached()) detach();
    }

    public void detach() {
        mainThread();
        if (observed != null && listener != null)
            observed.removeOnAttachStateChangeListener(listener);
        observed = null;
        listener = null;
        attachedChartId = -1;
        attachedRevision = -1L;
        bridge.detach();
    }

    /** Must be invoked from the owning Activity on destruction. */
    public void onHostDestroyed() {
        mainThread();
        enabled = false;
        detach();
    }

    public boolean isAttached() { return bridge.isAttached(); }

    private static void mainThread() {
        if (Looper.myLooper() != Looper.getMainLooper())
            throw new IllegalStateException("must run on Android UI thread");
    }
}
