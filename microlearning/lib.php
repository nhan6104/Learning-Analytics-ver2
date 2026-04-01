<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

defined('MOODLE_INTERNAL') || die();

defined('MOODLE_INTERNAL') || die();

require_once(__DIR__ . '/config.php');

/**
 * Get SQL Server configuration.
 */
function local_microlearning_get_config() {
    global $local_microlearning_config;
    
    $config = new stdClass();
    $config->host = $local_microlearning_config['host'] ?? '';
    $config->port = $local_microlearning_config['port'] ?? 5432;
    $config->database = $local_microlearning_config['database'] ?? '';
    $config->user = $local_microlearning_config['user'] ?? '';
    $config->password = $local_microlearning_config['password'] ?? '';
    
    return $config;
}

/**
 * Collect content data direct to SQL Server.
 */
function local_microlearning_collect_content_data($lastsynctime, $conn) {
    global $DB;

    $recordsprocessed = 0;
    
    $sql = "SELECT cm.id, cm.course, cm.instance, cm.module, cm.visible, cm.added,
                   m.name as module_type
            FROM {course_modules} cm
            JOIN {modules} m ON cm.module = m.id
            WHERE cm.added >= :lastsync
              AND cm.visible = 1
            ORDER BY cm.added ASC";

    $params = ['lastsync' => $lastsynctime];
    $coursemodules = $DB->get_records_sql($sql, $params);

    foreach ($coursemodules as $cm) {
        try {
            $contentdata = local_microlearning_get_module_content($cm);

            if ($contentdata) {
                $record = (array)$contentdata;
                $record['moodle_cmid'] = $cm->id;
                $record['created_at'] = $cm->added;
                $record['updated_at'] = $cm->added;
                
                local_microlearning_upsert_to_sqlserver($conn, 'microlearning_content', [$record], 'moodle_cmid');
                $recordsprocessed++;
            }
        } catch (\Exception $e) {
             mtrace("  Error processing course module {$cm->id}: " . $e->getMessage());
        }
    }

    return $recordsprocessed;
}

/**
 * Get content data for a specific module.
 */
function local_microlearning_get_module_content($cm) {
    global $DB;

    $content = new \stdClass();
    $content->courseid = $cm->course;
    $content->content_type = $cm->module_type;
    $content->is_active = $cm->visible;

    switch ($cm->module_type) {
        case 'resource':
            $resource = $DB->get_record('resource', ['id' => $cm->instance]);
            if ($resource) {
                $content->title = $resource->name;
                $content->description = $resource->intro ?? '';
                $fileinfo = local_microlearning_get_resource_file($cm->id);
                if ($fileinfo) {
                    $content->content_url = $fileinfo->filepath;
                    $content->duration_seconds = (int)local_microlearning_estimate_duration($fileinfo);
                    $content->metadata = json_encode([
                        'filesize' => $fileinfo->filesize,
                        'mimetype' => $fileinfo->mimetype
                    ]);
                }
            }
            break;

        case 'page':
            $page = $DB->get_record('page', ['id' => $cm->instance]);
            if ($page) {
                $content->title = $page->name;
                $content->description = $page->intro ?? '';
                $wordcount = str_word_count(strip_tags($page->content ?? ''));
                $content->duration_seconds = (int)round(max(60, ($wordcount / 200) * 60));
            }
            break;

        case 'url':
            $url = $DB->get_record('url', ['id' => $cm->instance]);
            if ($url) {
                $content->title = $url->name;
                $content->description = $url->intro ?? '';
                $content->content_url = $url->externalurl;
                $content->duration_seconds = 180;
            }
            break;

        case 'h5pactivity':
            $h5p = $DB->get_record('h5pactivity', ['id' => $cm->instance]);
            if ($h5p) {
                $content->title = $h5p->name;
                $content->description = $h5p->intro ?? '';
                $content->duration_seconds = 300;
            }
            break;

        case 'quiz':
            $quiz = $DB->get_record('quiz', ['id' => $cm->instance]);
            if ($quiz) {
                $content->title = $quiz->name;
                $content->description = $quiz->intro ?? '';
                $content->duration_seconds = (int)($quiz->timelimit ?? 600);
            }
            break;

        default:
            $modulename = $cm->module_type;
            $table = $modulename;
            if ($DB->get_manager()->table_exists($table)) {
                $record = $DB->get_record($table, ['id' => $cm->instance], 'name, intro');
                if ($record) {
                    $content->title = $record->name ?? '';
                    $content->description = $record->intro ?? '';
                    $content->duration_seconds = 180;
                }
            }
            break;
    }

    if (empty($content->title)) {
        return null;
    }

    $content->difficulty_level = 3;
    $content->view_count = 0;
    $content->completion_count = 0;

    return $content;
}

/**
 * Get file information.
 */
function local_microlearning_get_resource_file($cmid) {
    global $DB;

    $sql = "SELECT f.id, f.filename, f.filesize, f.mimetype, f.filepath, f.contenthash
            FROM {files} f
            WHERE f.component = 'mod_resource'
              AND f.filearea = 'content'
              AND f.itemid = :cmid
              AND f.filesize > 0
              AND f.filename != '.'
            ORDER BY f.filesize DESC
            LIMIT 1";

    return $DB->get_record_sql($sql, ['cmid' => $cmid]);
}

/**
 * Estimate duration.
 */
function local_microlearning_estimate_duration($fileinfo) {
    $mimetype = $fileinfo->mimetype ?? '';
    if (strpos($mimetype, 'video/') === 0) {
        $estimatedminutes = max(1, round($fileinfo->filesize / (1024 * 1024)));
        return min(300, $estimatedminutes * 60);
    }
    if (strpos($mimetype, 'audio/') === 0) {
        $estimatedminutes = max(1, round($fileinfo->filesize / (512 * 1024)));
        return min(300, $estimatedminutes * 60);
    }
    if (strpos($mimetype, 'pdf') !== false || strpos($mimetype, 'text') !== false) {
        $estimatedminutes = max(1, round($fileinfo->filesize / 1024));
        return min(300, $estimatedminutes * 60);
    }
    return 120;
}

/**
 * Collect activity data direct to SQL Server.
 */
function local_microlearning_collect_activity_data($lastsynctime, $conn) {
    global $DB;
    $recordsprocessed = 0;

    // Quiz
    $sql = "SELECT qa.id, qa.userid, qa.quiz, qa.attempt, qa.timestart, qa.timefinish,
                   qa.sumgrades, qa.state, q.grade as maxgrade
            FROM {quiz_attempts} qa
            JOIN {quiz} q ON qa.quiz = q.id
            WHERE qa.timemodified >= :lastsync
            ORDER BY qa.timemodified ASC";
            
    $quizattempts = $DB->get_records_sql($sql, ['lastsync' => $lastsynctime]);
    
    foreach ($quizattempts as $qa) {
         try {
            $cm = get_coursemodule_from_instance('quiz', $qa->quiz);
            if (!$cm) continue;
            
            $attemptdata = new stdClass();
            $attemptdata->userid = $qa->userid;
            $attemptdata->moodle_cmid = $cm->id; 
            $attemptdata->activity_type = 'quiz';
            $attemptdata->attempt_number = $qa->attempt;
            $attemptdata->source_attempt_id = $qa->id;
            $attemptdata->start_time = $qa->timestart;
            $attemptdata->submit_time = $qa->timefinish > 0 ? $qa->timefinish : null;
            $attemptdata->time_taken_seconds = $qa->timefinish > 0 ? ($qa->timefinish - $qa->timestart) : null;
            $attemptdata->score = $qa->sumgrades;
            $attemptdata->max_score = $qa->maxgrade;
            $attemptdata->percentage = $qa->maxgrade > 0 ? ($qa->sumgrades / $qa->maxgrade) * 100 : 0;
            $attemptdata->is_passed = ($qa->state === 'finished' && $attemptdata->percentage >= 50) ? 1 : 0;
            
            local_microlearning_upsert_to_sqlserver($conn, 'microlearning_activity_attempt', [$attemptdata], 'source_attempt_id');
            $recordsprocessed++;
         } catch (\Exception $e) { /* ignore */ }
    }
    
    // H5P
    $sql = "SELECT ha.id, ha.h5pactivityid, ha.userid, ha.attempt, ha.timecreated, ha.timemodified,
                   ha.rawscore, ha.maxscore, ha.duration, ha.completion, ha.success
            FROM {h5pactivity_attempts} ha
            WHERE ha.timemodified >= :lastsync
            ORDER BY ha.timemodified ASC";

    $h5pattempts = $DB->get_records_sql($sql, ['lastsync' => $lastsynctime]);

    foreach ($h5pattempts as $ha) {
        try {
            $cm = get_coursemodule_from_instance('h5pactivity', $ha->h5pactivityid);
            if (!$cm) continue;

            $attemptdata = new \stdClass();
            $attemptdata->userid = $ha->userid;
            $attemptdata->moodle_cmid = $cm->id;
            $attemptdata->activity_type = 'h5p';
            $attemptdata->attempt_number = $ha->attempt;
            $attemptdata->source_attempt_id = $ha->id;
            $attemptdata->start_time = $ha->timecreated;
            $attemptdata->submit_time = $ha->timemodified;
            $attemptdata->time_taken_seconds = $ha->duration;
            $attemptdata->score = $ha->rawscore;
            $attemptdata->max_score = $ha->maxscore;
            $attemptdata->percentage = $ha->maxscore > 0 ? ($ha->rawscore / $ha->maxscore) * 100 : 0;
            $attemptdata->is_passed = ($ha->success == 1) ? 1 : 0;

            local_microlearning_upsert_to_sqlserver($conn, 'microlearning_activity_attempt', [$attemptdata], 'source_attempt_id');
            $recordsprocessed++;
        } catch (\Exception $e) {}
    }
    
    return $recordsprocessed;
}

/**
 * Collect behavior data direct to SQL Server.
 */
function local_microlearning_collect_behavior_data($lastsynctime, $conn) {
    global $DB;
    $recordsprocessed = 0;
    
    if (!$DB->get_manager()->table_exists('logstore_standard_log')) {
        return 0;
    }

    $sql = "SELECT id, userid, courseid, contextinstanceid, component, action, crud,
                   timecreated, other
            FROM {logstore_standard_log}
            WHERE component LIKE 'mod_%'
              AND action IN ('viewed', 'submitted', 'started', 'updated', 'created', 'deleted',
                             'attempted', 'graded', 'answered', 'reviewed', 'played', 'paused', 'resumed')
              AND timecreated >= :lastsync
            ORDER BY timecreated ASC";

    $logs = $DB->get_records_sql($sql, ['lastsync' => $lastsynctime]);

    foreach ($logs as $log) {
        try {
            $interactiontype = local_microlearning_map_interaction_type($log);
            if (empty($interactiontype)) continue;

            $otherdata = [];
            if (!empty($log->other)) {
                $otherdata = json_decode($log->other, true);
            }
            if (!is_array($otherdata)) $otherdata = [];
            
            $otherdata['__action'] = $log->action;
            $otherdata['__component'] = $log->component;

            $interaction = new \stdClass();
            $interaction->userid = $log->userid;
            $interaction->moodle_cmid = $log->contextinstanceid; // Direct link to CMID
            $interaction->interaction_type = $interactiontype;
            $interaction->timestamp = $log->timecreated;
            $interaction->interaction_data = json_encode($otherdata);
            
            // For immutable logs, we can just insert, or try upsert if we track by ID?
            // Since we don't have a unique key easily mapped to Source ID (Log ID is unique though).
            // Let's use Log ID as tracking if we add 'source_log_id' column to SQL Server table.
            // Assuming we added that column. If not, we risk dupes if we sync same timestamp range.
            // For now, let's treat it as insert-only if we assume cron runs incrementally.
            // But to be safe, let's assume we have a unique constraint on (userid, moodle_cmid, timestamp, interaction_type) on SQL Server.
            // Or better: pass source_id.
            $interaction->source_log_id = $log->id;

            local_microlearning_upsert_to_sqlserver($conn, 'microlearning_learning_interaction', [$interaction], 'source_log_id');
            $recordsprocessed++;

        } catch (\Exception $e) {}
    }
    
    return $recordsprocessed;
}

/**
 * Map interaction type.
 */
function local_microlearning_map_interaction_type($log) {
    $action = strtolower($log->action ?? '');
    $component = strtolower($log->component ?? '');
    $crud = strtolower($log->crud ?? '');

    $basicmap = [
        'viewed' => 'view', 'submitted' => 'submit', 'started' => 'play',
        'attempted' => 'attempt', 'graded' => 'grade', 'answered' => 'answer',
        'reviewed' => 'review', 'played' => 'play', 'paused' => 'pause',
        'resumed' => 'resume', 'updated' => 'edit', 'created' => 'create',
        'deleted' => 'delete',
    ];

    if (isset($basicmap[$action])) return $basicmap[$action];

    if ($crud === 'c') return 'create';
    if ($crud === 'u') return 'edit';
    if ($crud === 'd') return 'delete';
    if ($crud === 'r') return 'view';

    if ($component === 'mod_quiz') {
        if (strpos($action, 'submit') !== false) return 'submit';
        if (strpos($action, 'attempt') !== false) return 'attempt';
    }

    return null;
}

/**
 * Log sync operation.
 */
function local_microlearning_log_sync($syncstart, $syncend, $recordsprocessed, $filesprocessed, $status, $errormessage) {
    global $DB;

    // We can log to Moodle DB just for monitoring the cron itself
    if ($DB->get_manager()->table_exists('microlearning_sync_log')) {
        $log = new \stdClass();
        $log->sync_start = $syncstart;
        $log->sync_end = $syncend;
        $log->records_processed = $recordsprocessed;
        $log->files_processed = $filesprocessed;
        $log->status = $status;
        $log->error_message = $errormessage;

        $DB->insert_record('microlearning_sync_log', $log);
    }
}

/**
 * Organize new files into folders by date.
 */
function local_microlearning_organize_files($lastsynctime) {
    global $CFG, $DB;

    $filesprocessed = 0;
    $basedir = get_config('local_microlearning', 'files_base_directory');
    if (empty($basedir)) {
        $basedir = $CFG->dataroot . '/microlearning_files';
    }

    if (!is_writable($CFG->dataroot)) return 0;

    try {
        if (!check_dir_exists($basedir, true, true)) return 0;
        if (!is_writable($basedir)) return 0;
    } catch (\Exception $e) {
        return 0;
    }

    $sql = "SELECT f.id, f.contenthash, f.filename, f.filepath, f.timecreated,
                   f.component, f.filearea, f.itemid, f.mimetype, f.filesize
            FROM {files} f
            WHERE f.filesize > 0
              AND f.filename != '.'
              AND f.timecreated >= :lastsync
            ORDER BY f.timecreated ASC";

    $files = $DB->get_records_sql($sql, ['lastsync' => $lastsynctime]);

    foreach ($files as $file) {
        try {
            $tracking = $DB->get_record('microlearning_file_tracking', ['file_id' => $file->id]);
            if ($tracking) continue;

            $filepath = $CFG->dataroot . '/filedir/' . substr($file->contenthash, 0, 2) . '/' . substr($file->contenthash, 2, 2) . '/' . $file->contenthash;
            if (!file_exists($filepath)) continue;

            $filedate = date('Y-m-d', $file->timecreated);
            $targetdir = $basedir . '/' . $filedate;
            if (!check_dir_exists($targetdir, true, true)) continue;

            $targetpath = $targetdir . '/' . $file->contenthash . '_' . $file->filename;

            if (copy($filepath, $targetpath)) {
                $tracking = new \stdClass();
                $tracking->file_id = $file->id;
                $tracking->contenthash = $file->contenthash;
                $tracking->original_path = $filepath;
                $tracking->new_path = $targetpath;
                $tracking->sync_date = $filedate;
                $tracking->processed_at = time();
                $DB->insert_record('microlearning_file_tracking', $tracking);
                $filesprocessed++;
            }
        } catch (\Exception $e) {}
    }

    return $filesprocessed;
}

/**
 * Get PDO connection to SQL Server.
 */
function local_microlearning_get_sqlserver_connection() {
    $config = local_microlearning_get_config();

    if (empty($config->host) || empty($config->database)) {
        return null;
    }

    $dsn = "pgsql:host={$config->host};port={$config->port};dbname={$config->database};sslmode=require";
    
    try {
        $conn = new PDO($dsn, $config->user, $config->password);
        $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        return $conn;
    } catch (PDOException $e) {
         error_log("Database Connection Error (PG): " . $e->getMessage());
         if (CLI_SCRIPT) {
             mtrace("  Database Connection Error: " . $e->getMessage());
         }
         return null;
    }
}

/**
 * Upsert records to SQL Server.
 */
function local_microlearning_upsert_to_sqlserver($conn, $table, $records, $keyfield = 'id') {
    if (empty($records)) {
        return 0;
    }

    $count = 0;
    foreach ($records as $record) {
        $record = (array)$record;
        
        try {
            $checksql = "SELECT COUNT(*) FROM {$table} WHERE {$keyfield} = ?";
            $stmt = $conn->prepare($checksql);
            $stmt->execute([$record[$keyfield]]);
            $exists = $stmt->fetchColumn() > 0;

            if ($exists) {
                // Update
                $fields = [];
                $values = [];
                foreach ($record as $key => $value) {
                    if ($key === $keyfield) continue;
                    $fields[] = "{$key} = ?";
                    $values[] = $value;
                }
                $values[] = $record[$keyfield];
                
                $sql = "UPDATE {$table} SET " . implode(', ', $fields) . " WHERE {$keyfield} = ?";
                $conn->prepare($sql)->execute($values);
            } else {
                // Insert
                $has_id = isset($record['id']);
                
                try {
                    if ($has_id) {
                        $conn->exec("SET IDENTITY_INSERT {$table} ON");
                    }
                } catch (\Exception $e) {}

                $keys = array_keys($record);
                $binds = array_fill(0, count($keys), '?');
                $sql = "INSERT INTO {$table} (" . implode(', ', $keys) . ") VALUES (" . implode(', ', $binds) . ")";
                $conn->prepare($sql)->execute(array_values($record));
                
                try {
                    if ($has_id) {
                        $conn->exec("SET IDENTITY_INSERT {$table} OFF");
                    }
                } catch (\Exception $e) {}
            }
            $count++;
        } catch (\Exception $e) {
             mtrace("    Error exporting record {$record[$keyfield]} to {$table}: " . $e->getMessage());
        }
    }

    return $count;
}



