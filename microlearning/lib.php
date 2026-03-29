<?php
/**
 * Library functions for local_microlearning plugin
 * 
 * @package     local_microlearning
 * @copyright   2024
 * @license     http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

/**
 * Establish PostgreSQL connection to Datamart
 * 
 * Reads database credentials from environment variables or Moodle config
 * and returns a PDO connection object for querying the Datamart schema.
 * 
 * @return PDO|false PDO connection object on success, false on failure
 */
function local_microlearning_get_sqlserver_connection() {
    global $CFG;
    
    try {
        // Read database credentials from environment variables
        // These should be configured in the server environment or .env file
        $host = getenv('PGSQL_HOST') ?: 'localhost';
        $port = getenv('PGSQL_PORT') ?: '5432';
        $dbname = getenv('PGSQL_DBNAME') ?: 'datamart';
        $user = getenv('PGSQL_USER') ?: 'postgres';
        $password = getenv('PGSQL_PASSWORD') ?: '';
        $sslmode = getenv('PGSQL_SSL_MODE') ?: 'prefer';
        $sslrootcert = getenv('PGSQL_SSL_ROOT_CERT') ?: '';
        
        // Build DSN (Data Source Name)
        $dsn = "pgsql:host={$host};port={$port};dbname={$dbname};sslmode={$sslmode}";
        
        // Add SSL root certificate if provided
        if (!empty($sslrootcert) && file_exists($sslrootcert)) {
            $dsn .= ";sslrootcert={$sslrootcert}";
        }
        
        // Create PDO connection
        $conn = new PDO($dsn, $user, $password, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ]);
        
        return $conn;
        
    } catch (PDOException $e) {
        // Log error for debugging
        error_log('PostgreSQL connection failed: ' . $e->getMessage());
        return false;
    }
}
