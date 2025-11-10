<?php
require_once __DIR__ . '/../config/supabase.php';

class CommentModel {
    public function predictSentiment($text) {
        if (empty(trim($text))) return 1;
        $scriptPath = realpath(__DIR__ . '/../Model_ML/predict.py');
        if (!file_exists($scriptPath)) return 1;

        $pythonCommands = [PHP_OS_FAMILY === 'Windows' ? 'python' : '/usr/bin/python3', PHP_OS_FAMILY === 'Windows' ? 'python3' : '/usr/bin/python'];
        $text = mb_convert_encoding($text, 'UTF-8', 'UTF-8');
        $escapedText = escapeshellarg($text);
        $escapedScript = escapeshellarg($scriptPath);

        foreach ($pythonCommands as $cmd) {
            $check = shell_exec((PHP_OS_FAMILY === 'Windows' ? "where $cmd" : "which $cmd") . " 2>&1");
            if (empty($check)) continue;

            $command = (PHP_OS_FAMILY === 'Windows')
                ? "set PYTHONIOENCODING=utf-8 && $cmd $escapedScript $escapedText 2>&1"
                : "PYTHONIOENCODING=utf-8 $cmd $escapedScript $escapedText 2>&1";

            $output = trim(shell_exec($command) ?? '');
            if ($output !== '' && stripos($output, 'Traceback') === false) {
                return is_numeric($output) ? ((int)$output === 0 ? 0 : 1) : (stripos($output, 'neg') !== false ? 0 : 1);
            }
        }
        return 1;
    }

    public function addReview($user_id, $product_id, $content, $rating = null, $images = null) {
        $sentiment = $this->predictSentiment($content);
        $data = [
            'ma_nguoi_dung' => $user_id,
            'ma_san_pham' => $product_id,
            'noi_dung_danh_gia' => $content,
            'diem_danh_gia' => $rating,
            'trang_thai' => $sentiment,
            'thoi_gian_tao' => date('Y-m-d H:i:s'),
            'thoi_gian_cap_nhat' => date('Y-m-d H:i:s'),
            'trang_thai_phan_hoi' => 0
        ];

        $insert = supabase_request('POST', 'reviews', [], $data);
        if (is_string($insert)) $insert = json_decode($insert, true);

        $ma_danh_gia = $this->getLastInsertedReviewId();
        if ($ma_danh_gia && !empty($images)) {
            if (!is_array($images)) $images = [$images];
            foreach ($images as $img) {
                if (empty($img)) continue;
                $img_data = [
                    'ma_danh_gia' => $ma_danh_gia,
                    'duong_dan_anh' => $img,
                    'thoi_gian_tao' => date('Y-m-d H:i:s'),
                    'thoi_gian_cap_nhat' => date('Y-m-d H:i:s')
                ];
                supabase_request('POST', 'review_images', [], $img_data);
            }
        }
        return ['error' => false, 'message' => 'Lưu bình luận thành công'];
    }

    public function getLastInsertedReviewId() {
        $res = supabase_request('GET', 'reviews', [
            'select' => 'ma_danh_gia',
            'order' => 'ma_danh_gia.desc',
            'limit' => 1
        ]);
        if (is_string($res)) $res = json_decode($res, true);
        return $res['data'][0]['ma_danh_gia'] ?? null;
    }

    public function getAllReviewsFlat($filter = 'all', $rating = null, $replyStatus = null, $page = 1, $perPage = 20) {
        $params = [
            'select' => '*, users:ma_nguoi_dung(ten_nguoi_dung), products:ma_san_pham(ten_san_pham), review_images(ma_hinh_anh, duong_dan_anh)',
            'order' => 'thoi_gian_tao.desc'
        ];

        if ($filter === 'positive') $params['trang_thai'] = 'eq.1';
        elseif ($filter === 'hidden') $params['trang_thai'] = 'eq.0';
        elseif ($filter === 'display') $params['trang_thai'] = 'eq.1';
        elseif ($filter === 'image') $params['review_images.duong_dan_anh'] = 'not.is.null';

        if (!empty($rating)) $params['diem_danh_gia'] = "eq.$rating";
        if ($replyStatus === '1') $params['trang_thai_phan_hoi'] = 'eq.1';
        elseif ($replyStatus === '0') $params['trang_thai_phan_hoi'] = 'eq.0';

        $offset = ($page - 1) * $perPage;
        $params['limit'] = $perPage;
        $params['offset'] = $offset;

        $res = supabase_request('GET', 'reviews', $params);
        if (is_string($res)) $res = json_decode($res, true);

        if (!isset($res['data']) || !is_array($res['data'])) return [];

        foreach ($res['data'] as &$review) {
            $review['hinh_anh'] = [];
            if (!empty($review['review_images']) && is_array($review['review_images'])) {
                foreach ($review['review_images'] as $img) {
                    if (!empty($img['duong_dan_anh'])) $review['hinh_anh'][] = $img['duong_dan_anh'];
                }
            }
            unset($review['review_images']);
        }

        return $res['data'];
    }

    public function countReviews($filter = 'all', $rating = null, $replyStatus = null) {
        $params = ['select' => 'count'];
        if ($filter === 'positive') $params['trang_thai'] = 'eq.1';
        elseif ($filter === 'hidden') $params['trang_thai'] = 'eq.0';
        elseif ($filter === 'display') $params['trang_thai'] = 'eq.1';
        elseif ($filter === 'image') $params['review_images.duong_dan_anh'] = 'not.is.null';
        if (!empty($rating)) $params['diem_danh_gia'] = "eq.$rating";
        if ($replyStatus === '1') $params['trang_thai_phan_hoi'] = 'eq.1';
        elseif ($replyStatus === '0') $params['trang_thai_phan_hoi'] = 'eq.0';

        $res = supabase_request('GET', 'reviews', $params);
        if (is_string($res)) $res = json_decode($res, true);
        return $res['data'][0]['count'] ?? 0;
    }

    public function replyReview($review_id, $reply) {
        if (empty(trim($reply))) return ['error' => true, 'message' => 'Nội dung trống'];

        $res = supabase_request('GET', 'reviews', [
            'select' => 'ma_san_pham, ma_danh_gia_cha',
            'ma_danh_gia' => "eq.$review_id"
        ]);
        if (is_string($res)) $res = json_decode($res, true);
        if (empty($res['data'][0])) return ['error' => true, 'message' => 'Không tìm thấy bình luận cha'];

        $review = $res['data'][0];
        $ma_san_pham = $review['ma_san_pham'];
        $sentiment = $this->predictSentiment($reply);

        $data = [
            'ma_danh_gia_cha' => $review_id,
            'noi_dung_danh_gia' => $reply,
            'ma_nguoi_dung' => 1,
            'ma_san_pham' => $ma_san_pham,
            'diem_danh_gia' => null,
            'trang_thai' => $sentiment,
            'thoi_gian_tao' => date('Y-m-d H:i:s'),
            'thoi_gian_cap_nhat' => date('Y-m-d H:i:s'),
            'trang_thai_phan_hoi' => 1
        ];

        supabase_request('POST', 'reviews', [], $data);
        supabase_request('PATCH', 'reviews', ['ma_danh_gia' => "eq.$review_id"], ['trang_thai_phan_hoi' => 1]);

        return ['error' => false, 'message' => 'Phản hồi thành công'];
    }

    public function changeStatus($id, $status) {
        $body = [];
        if ($status === 'display') $body = ['trang_thai' => 1];
        elseif ($status === 'hidden') $body = ['trang_thai' => 0];
        elseif ($status === 'deleted') $body = ['trang_thai' => -1];
        return supabase_request('PATCH', 'reviews', ['ma_danh_gia' => "eq.$id"], $body);
    }

    public function deleteReviewAndReplies($id) {
        $replies = supabase_request('GET', 'reviews', [
            'select' => 'ma_danh_gia',
            'ma_danh_gia_cha' => "eq.$id"
        ]);
        if (is_string($replies)) $replies = json_decode($replies, true);

        foreach ($replies['data'] ?? [] as $reply) {
            $this->deleteReviewAndReplies($reply['ma_danh_gia']);
        }

        return supabase_request('DELETE', 'reviews', ['ma_danh_gia' => "eq.$id"]);
    }

    public function deleteAllReviews() {
        $res = supabase_request('DELETE', 'reviews', []);
        if (is_string($res)) $res = json_decode($res, true);
        return !empty($res['error']) ? ['error' => true, 'message' => 'Xóa lỗi'] : ['error' => false, 'message' => 'Đã xóa tất cả'];
    }
}
?>