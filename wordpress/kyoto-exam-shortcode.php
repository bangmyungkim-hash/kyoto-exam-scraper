<?php
/**
 * 京都高校受験情報 ショートコード
 *
 * aioijuku.com の functions.php に追記して使う
 *
 * 使い方:
 *   [kyoto_exam type="public"]  → 公立高校入試情報
 *   [kyoto_exam type="private"] → 私立高校・説明会情報
 */

// GitHub Raw URL（リポジトリが public の場合）
define('KYOTO_EXAM_REPO_RAW', 'https://raw.githubusercontent.com/bangmyungkim-hash/kyoto-exam-scraper/main/data/');

function kyoto_exam_shortcode($atts) {
    $atts = shortcode_atts(['type' => 'public'], $atts);
    $type = $atts['type'] === 'private' ? 'school_events' : 'public_exam';

    // 週1回キャッシュ
    $cache_key = 'kyoto_exam_' . $type;
    $data = get_transient($cache_key);

    if ($data === false) {
        $url = KYOTO_EXAM_REPO_RAW . $type . '.json';
        $response = wp_remote_get($url, ['timeout' => 15]);

        if (is_wp_error($response)) {
            return '<p>データ取得中にエラーが発生しました。</p>';
        }

        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);

        if (!$data) {
            return '<p>データを取得できませんでした。しばらくお待ちください。</p>';
        }

        set_transient($cache_key, $data, WEEK_IN_SECONDS);
    }

    ob_start();
    $updated = isset($data['updated_at'])
        ? date('Y年n月j日', strtotime($data['updated_at']))
        : '—';
    ?>
    <div class="kyoto-exam-wrap">
      <p class="kyoto-exam-updated" style="background:#f0f7ff;border-left:4px solid #3b82f6;padding:10px 14px;border-radius:4px;">
        📅 最終更新: <?php echo esc_html($updated); ?>（自動更新）
      </p>

      <?php if ($atts['type'] === 'public'): ?>
        <?php kyoto_exam_render_public($data); ?>
      <?php else: ?>
        <?php kyoto_exam_render_private($data); ?>
      <?php endif; ?>

      <p style="font-size:0.85em;color:#666;margin-top:2em;">
        ※掲載情報は自動収集データです。受験前に必ず各学校・京都府教育委員会の公式サイトでご確認ください。
      </p>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode('kyoto_exam', 'kyoto_exam_shortcode');


function kyoto_exam_render_public($data) {
    $schedule = $data['schedule'] ?? [];
    $schools  = $data['schools'] ?? [];

    // 入試日程
    if (!empty($schedule['schedule'])): ?>
    <h2>入試日程</h2>
    <table><thead><tr><th>区分</th><th>日程</th></tr></thead><tbody>
    <?php foreach ($schedule['schedule'] as $s): ?>
      <tr><td><?php echo esc_html($s['event']); ?></td><td><?php echo esc_html($s['date']); ?></td></tr>
    <?php endforeach; ?>
    </tbody></table>
    <p><a href="<?php echo esc_url($schedule['official_url'] ?? 'https://www.kyoto-be.ne.jp/ed-top/'); ?>" target="_blank" rel="noopener">▶ 京都府教育委員会 公式サイト</a></p>
    <?php endif;

    // 学校一覧
    if (!empty($schools)): ?>
    <h2>学校別 偏差値・倍率一覧</h2>
    <p style="font-size:0.85em;">出典：<a href="https://www.minkou.jp/" target="_blank" rel="noopener">みんなの高校情報</a></p>
    <table><thead><tr><th>学校名</th><th>偏差値</th><th>倍率</th><th>所在地</th></tr></thead><tbody>
    <?php foreach (array_slice($schools, 0, 30) as $s):
        $ratio = !empty($s['bairitsu']) ? ($s['bairitsu'][0]['ratio'] ?? '—') : '—';
    ?>
      <tr>
        <td><a href="<?php echo esc_url($s['url']); ?>" target="_blank" rel="noopener"><?php echo esc_html($s['name']); ?></a></td>
        <td><?php echo esc_html($s['hensachi'] ?? '—'); ?></td>
        <td><?php echo esc_html($ratio); ?></td>
        <td><?php echo esc_html($s['area'] ?? '—'); ?></td>
      </tr>
    <?php endforeach; ?>
    </tbody></table>
    <?php endif;
}


function kyoto_exam_render_private($data) {
    $calendar = $data['events']['calendar'] ?? [];
    $official = $data['events']['official'] ?? [];
    $schools  = $data['private_schools'] ?? [];

    // 説明会カレンダー
    if (!empty($calendar)): ?>
    <h2>説明会・オープンキャンパス 直近日程</h2>
    <table><thead><tr><th>日程</th><th>学校名</th><th>イベント</th></tr></thead><tbody>
    <?php foreach (array_slice($calendar, 0, 20) as $e): ?>
      <tr>
        <td><?php echo esc_html($e['date'] ?? '—'); ?></td>
        <td><?php echo esc_html($e['school'] ?? '—'); ?></td>
        <td><?php echo esc_html($e['event'] ?? '—'); ?></td>
      </tr>
    <?php endforeach; ?>
    </tbody></table>
    <?php endif;

    // 公式サイト情報
    if (!empty($official)): ?>
    <h2>各校公式サイト情報</h2>
    <ul>
    <?php foreach (array_slice($official, 0, 15) as $e): ?>
      <li><strong><?php echo esc_html($e['school']); ?></strong>：<?php echo esc_html($e['text']); ?>
        （<a href="<?php echo esc_url($e['source']); ?>" target="_blank" rel="noopener">公式サイト</a>）</li>
    <?php endforeach; ?>
    </ul>
    <?php endif;

    // 私立高校一覧
    if (!empty($schools)): ?>
    <h2>京都府私立高校 偏差値一覧</h2>
    <p style="font-size:0.85em;">出典：<a href="https://www.minkou.jp/" target="_blank" rel="noopener">みんなの高校情報</a></p>
    <table><thead><tr><th>学校名</th><th>偏差値</th><th>所在地</th></tr></thead><tbody>
    <?php foreach (array_slice($schools, 0, 20) as $s): ?>
      <tr>
        <td><a href="<?php echo esc_url($s['url']); ?>" target="_blank" rel="noopener"><?php echo esc_html($s['name']); ?></a></td>
        <td><?php echo esc_html($s['hensachi'] ?? '—'); ?></td>
        <td><?php echo esc_html($s['area'] ?? '—'); ?></td>
      </tr>
    <?php endforeach; ?>
    </tbody></table>
    <?php endif;
}
